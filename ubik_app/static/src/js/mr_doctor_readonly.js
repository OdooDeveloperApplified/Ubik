/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";

patch(FormController.prototype, {

    setup() {
        super.setup();

        useEffect(() => {
            this._applyMRDoctorReadonly();
        }, () => [
            this.model.root?.data?.record_save,
            this.model.root?.data?.unlock_for_edit
        ]);
    },

    _applyMRDoctorReadonly() {
        const record = this.model.root;

        if (!record || !record.data) {
            return;
        }

        if (record.resModel !== "mr.doctor") {
            return;
        }

        const isPastMonth = !!record.data.record_save;
        const isUnlocked = !!record.data.unlock_for_edit;

        // 🔥 Correct logic
        const shouldLock = isPastMonth && !isUnlocked;

        if (shouldLock) {
            record.isReadonly = true;

            if (this.mode === "edit") {
                this.switchMode("readonly");
            }

            if (this.archInfo?.activeActions) {
                this.archInfo.activeActions.edit = false;
            }

        } else {
            record.isReadonly = false;

            if (this.archInfo?.activeActions) {
                this.archInfo.activeActions.edit = true;
            }
        }
    },
});