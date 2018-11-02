define(['Vue', 'paper', 'axios', 'categoryCard', 'asyncStatus'],
    function (Vue, paper, axios) {

    let categories = new Vue({
        el: '#app',
        data: {
            categoryCount: 0,
            pages: 1,
            page: 1,
            limit: 50,
            range: 11,
            createName: "",
            categories: [],
            status: {
                data: {state: true, message: 'Loading categories'},
            },
        },
        methods: {
            updatePage: function () {
                this.status.data.state = false;
                axios
                    .get('/api/category/data', {
                        params: {
                            page: this.page,
                            limit: this.limit
                        }
                    })
                    .then((response) => {

                        this.categories = response.data.categories;
                        this.page = response.data.pagination.page;
                        this.pages = response.data.pagination.pages;
                        this.categoryCount = response.data.pagination.total;

                        this.status.data.state = true;
                    })
            },
            createCategory: function () {
                if (this.createName.length < 1) return;

                axios.post("/api/category/", {
                    name: this.createName
                }).then(response => {
                    this.createName = "";
                    this.updatePage()
                });
            },
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
        computed: {
        },
        created() {
            axios.baseURL = window.location.origin;
            this.updatePage();

        }

    });
});