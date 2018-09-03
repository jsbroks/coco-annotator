define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('pagination', {
        props: {
            pages: {
                type: Number,
                required: true,
            },
        },
        data: function () {
            return {
                range: 11,
                page: 1,
                timer: null
            }
        },
        template: `
            <div class="row justify-content-md-center">
                <ul class="pagination text-center">
                    <li :class="{ 'page-item': true, disabled: page == 1 }" @click="previousPage">
                        <a class="page-link" aria-label="Previous">
                            <span aria-hidden="true">&laquo;</span>
                            <span class="sr-only">Previous</span>
                        </a>
                    </li>

                    <li v-for="pageIndex in range" :class="{ 'page-item': true, active: pageIndex + startPage == page }">
                        <a class="page-link" @click="page = pageIndex + startPage">{{ pageIndex + startPage}}</a>
                    </li>

                    <li :class="{ 'page-item': true, disabled: page == pages }" @click="nextPage">
                        <a class="page-link" aria-label="Next">
                            <span aria-hidden="true">&raquo;</span>
                            <span class="sr-only">Next</span>
                        </a>
                    </li>
                </ul>
            </div>
        `,
        methods: {
            previousPage: function () {
                this.page -= 1;
                if (this.page < 1) {
                    this.page = 1
                }
            },
            nextPage: function () {
                this.page += 1;
                if (this.page > this.pages) {
                    this.page = this.pages
                }
            }
        },
        watch: {
            page: function (newPage, oldPage) {
                if (newPage === oldPage) return;

                clearTimeout(this.timer);
                this.timer = setTimeout(() => this.$emit('pagechange', this.page), 500)
            }
        },
        computed: {
            startPage: function () {

                if (this.range > this.pages) {
                    this.range = this.pages;
                    return 0;
                }

                let range = Math.round(this.range / 2);
                let start = this.page - range;

                if (start < 0) return 0;

                if (start > this.pages || start + this.range > this.pages) {
                    return this.pages - this.range;
                }

                return start
            }
        },
        created () {
        }
    });
});
