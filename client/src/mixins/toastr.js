export default {
  methods: {
    axiosReqestError(title, message) {
      let options = {
        progressBar: true,
        positionClass: "toast-bottom-left"
      };

      this.$toastr.error(message, title, options);
    }
  }
};
