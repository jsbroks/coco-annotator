define(['Vue', 'paper', 'axios', 'asyncStatus'],
    function (Vue, paper, axios) {

    let undo = new Vue({
        el: '#app',
        data: {
            undos: [],
            status: {
                data: {state: true, message: 'Loading data'},
            }
        },
        methods: {
            updatePage: function () {
                this.status.data.state = false;
                axios
                    .get('/api/undo/list/')
                    .then((response) => {

                        this.undos = response.data;

                        this.status.data.state = true;
                    })
            },
            undoModel: function (id, instance) {
                axios.post('/api/undo/?id=' + id + '&instance=' + instance).then(response => {
                    this.updatePage()
                });
            },
            deleteModel: function (id, instance) {
                axios.delete('/api/undo/?id=' + id + '&instance=' + instance).then(response => {
                    this.updatePage()
                });
            }

        },
        created() {
            axios.baseURL = window.location.origin;
            this.updatePage()
        }

    });
});