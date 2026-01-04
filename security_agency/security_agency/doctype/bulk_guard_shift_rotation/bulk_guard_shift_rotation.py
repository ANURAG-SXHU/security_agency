# Copyright (c) 2025, Anurag Sahu
# For license information, please see license.txt
import frappe
from frappe.model.document import Document


class BulkGuardShiftRotation(Document):

    # --------------------------------------------------
    # VALIDATIONS
    # --------------------------------------------------

    def validate(self):
        self._validate_rotation_template()
        self._validate_employees()

    def _validate_rotation_template(self):
        if not self.rotation_template:
            frappe.throw("Rotation Template cannot be empty")

    def _validate_employees(self):
        selected = [
            e for e in self.bulk_guard_rotation_employee if e.include
        ]
        if not selected:
            frappe.throw("Please select at least one employee")

    # --------------------------------------------------
    # SUBMIT
    # --------------------------------------------------

    def on_submit(self):
        self._create_guard_shift_rotations()

    def _create_guard_shift_rotations(self):
        created = 0
        skipped = 0

        CHILD_FIELD = "guard_shift_rotation_item"

        for emp in self.bulk_guard_rotation_employee:
            if not emp.include:
                continue

            # Avoid duplicate rotations
            exists = frappe.db.exists(
                "Guard Shift Rotation",
                {
                    "site": self.site,
                    "guard": emp.employee,
                    "day_of_week": self.day_of_week,
                }
            )

            if exists:
                skipped += 1
                continue

            rotation = frappe.new_doc("Guard Shift Rotation")
            rotation.site = self.site
            rotation.guard = emp.employee
            rotation.day_of_week = self.day_of_week
            rotation.rotation_start_date = self.rotation_start_date

            # Append rotation sequence
            for r in self.rotation_template:
                rotation.append(CHILD_FIELD, {
                    "order": r.order,
                    "shift_type": r.shift_type
                })

            rotation.insert(ignore_permissions=True)
            created += 1

        frappe.msgprint(
            f"""
            Guard Shift Rotations created: <b>{created}</b><br>
            Skipped (already existed): <b>{skipped}</b>
            """,
            indicator="green"
        )

    # --------------------------------------------------
    # BUTTON METHOD (WHITELISTED)
    # --------------------------------------------------

    # @frappe.whitelist()
    # def fetch_employees(self):
    #     if not self.site:
    #         frappe.throw("Please select Site first")

    #     # Step 1: Get guards assigned to this site
    #     assigned_guards = frappe.get_all(
    #         "Deployment Line",
    #         filters={"site": self.site},
    #         distinct=True,
    #         pluck="guard"
    #     )

    #     if not assigned_guards:
    #         self.set("bulk_guard_rotation_employee", [])
    #         frappe.msgprint("No guards assigned to this site")
    #         return 0

    #     # Step 2: Build filters
    #     filters = {
    #         "name": ["in", assigned_guards]
    #     }

    #     if self.designation:
    #         filters["designation"] = self.designation

    #     if self.employee_status == "Active":
    #         filters["status"] = "Active"

    #     # Step 3: Fetch employees
    #     employees = frappe.get_all(
    #         "Employee",
    #         filters=filters,
    #         fields=["name", "employee_name", "designation"]
    #     )

    #     # Step 4: Populate child table
    #     self.set("bulk_guard_rotation_employee", [])

    #     for emp in employees:
    #         self.append("bulk_guard_rotation_employee", {
    #             "employee": emp.name,
    #             "employee_name": emp.employee_name,
    #             "designation": emp.designation,
    #             "include": 1
    #         })

    #     frappe.msgprint(
    #         f"Fetched {len(employees)} employees for site {self.site}",
    #         indicator="green"
    #     )

    #     return len(employees)
    @frappe.whitelist()
    def fetch_employees(self):
        if not self.site:
            frappe.throw("Please select Site first")

        # ----------------------------------
        # Build Employee Filters
        # ----------------------------------
        filters = {
            "custom_site": self.site
        }

        if self.designation:
            filters["designation"] = self.designation

        if self.employee_status == "Active":
            filters["status"] = "Active"

        # ----------------------------------
        # Fetch Employees
        # ----------------------------------
        employees = frappe.get_all(
            "Employee",
            filters=filters,
            fields=["name", "employee_name", "designation"]
        )

        if not employees:
            self.set("bulk_guard_rotation_employee", [])
            frappe.msgprint(
                f"No guards found for site {self.site}",
                indicator="orange"
            )
            return 0

        # ----------------------------------
        # Populate Child Table
        # ----------------------------------
        self.set("bulk_guard_rotation_employee", [])

        for emp in employees:
            self.append("bulk_guard_rotation_employee", {
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "designation": emp.designation,
                "include": 1
            })

        frappe.msgprint(
            f"Fetched {len(employees)} guards for site {self.site}",
            indicator="green"
        )

        return len(employees)

