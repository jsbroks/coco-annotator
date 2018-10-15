define(['Vue'], function (Vue) {

    Vue.component('async-status', {
        props: {
            status: {
                type: Object,
                required: true,
            },
        },
        data: function () {
            return {
                message: '',
                classes: "btn-outline-danger my-sm-0 btn-sm disabled"
            }
        },
        template: `
            <div class="form-inline my-2 my-lg-0" style="margin-right: 10px">
                <div :class="classes" style="border: none">
                    
                    <i v-if="allLoaded" class="fa fa-check fa-x status-icon" style="float:left"></i>
                    <i v-else class="fa fa-spinner fa-pulse fa-x fa-fw status-icon"></i>
                    
                    {{ message }}
                </div>
            </div>
        `,
        watch: {
            allLoaded: function (newVal, oldVal) {
                if (newVal) {
                    this.message = "Done";
                    this.classes = "btn-outline-success my-sm-0 btn-sm disabled";
                } else {
                    this.classes = "btn-outline-danger my-sm-0 btn-sm disabled";
                }
            }
        },
        computed: {
            allLoaded: function () {
                let loaded = true;

                for (let key in this.status) {
                    if (!this.status.hasOwnProperty(key)) continue;

                    let status = this.status[key];
                    if (status.state) continue;

                    this.message = status.message + '...';
                    loaded = false;
                    break;
                }

                return loaded
            }
        },
        created () {

        }
    });
});
