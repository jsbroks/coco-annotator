define(['Vue', 'paper', 'axios', 'imageCard', 'pagination', 'asyncStatus'],
    function (Vue, paper, axios) {

    let images = new Vue({
        el: '#app',
        data: {
            pages: 1,
            range: 11,
            limit: 52,
            imageCount: 0,
            images: [],
            folders: [],
            dataset: {
                id: 0
            },
            subdirectories: [],
            status: {
                data: {state: true, message: 'Loading data'},
            }
        },
        methods: {
            updatePage: function (page) {
                this.status.data.state = false;
                axios
                    .get('/api/dataset/' + this.dataset.id + '/data', {
                        params: {
                            page: page,
                            limit: this.limit
                        }
                    })
                    .then((response) => {

                        this.images = response.data.images;
                        this.dataset = response.data.dataset;

                        this.imageCount = response.data.pagination.total;
                        this.pages = response.data.pagination.pages;

                        this.subdirectories = response.data.subdirectories;

                        this.status.data.state = true;
                    })
            },
        },
        watch: {
        },
        computed: {
        },
        created() {
            axios.baseURL = window.location.origin;
            let pathname = window.location.pathname.split('/');
            this.dataset.id = parseInt(pathname[pathname.length - 1]);
            this.updatePage();
        }

    });
});