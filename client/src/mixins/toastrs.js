import { tr } from "@/i18n";

export default {
  methods: {
    axiosReqestError(title, message) {
      let options = {
        progressBar: true,
        positionClass: "toast-bottom-left"
      };

      this.$toastr.error(tr("toast", message), tr("toast", title), options);
    },
    axiosReqestSuccess(title, message) {
      let options = {
        progressBar: true,
        positionClass: "toast-bottom-left"
      };

      this.$toastr.success(tr("toast", message), tr("toast", title), options);
    }
  }
};
