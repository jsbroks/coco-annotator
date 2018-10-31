define(['Vue', 'paper', 'axios', 'datasetCard', 'asyncStatus'],
    function (Vue, paper, axios) {

    let datasets = new Vue({
        el: '#app',
        data: {
            api: '',
            pages: 1,
            page: 1,
            limit: 20,
            createName: '',
            createCategories: [],
            displayAmount: 0,
            datasets: [],
            subdirectories: [],
            status: {
                data: {state: true, message: 'Loading datasets'},
                downloading: {state: true, message: 'Downloading data'},
            },
            categories: []
        },
        methods: {
            updatePage: function () {
                this.status.data.state = false;
                axios
                    .get('/api/dataset/data')
                    .then((response) => {

                        this.datasets = response.data.datasets;
                        this.categories = response.data.categories;
                        this.page = response.data.page;
                        this.pages = response.data.pages;
                        this.subdirectories = response.data.subdirectories;

                        this.status.data.state = true;
                    })
            },
            createDataset: function () {
                if (this.createName.length < 1) return;

                let categories = [];

                for (let key in this.createCategories) {
                    categories.push(this.createCategories[key])
                }

                axios.post("/api/dataset/?name=" + this.createName, {
                    "categories": categories
                }).then(response => {
                    this.createName = "";
                    this.createCategories = [];
                    this.updatePage()
                });
            },
        },
        computed: {
            createDirectory: function () {
                return '/data/datasets/' + this.createName + '/';
            }
        },

        created() {
            axios.baseURL = window.location.origin;
            this.updatePage();

        }

    });
});