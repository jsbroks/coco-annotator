define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('metadata', {
        model: {
            prop: 'metadata',
            event: 'change'
        },
        props: {
            metadata: {
                type: Object,
                required: true
            }
        },
        data: function () {
            return {
                metadataList: []
            }
        },
        template: `
            <div>
                <i class="fa fa-plus" style="float: right; margin: 0 4px; color: green"
                    @click="createMetadata"></i>
                    
                <p style="margin: 0">Metadata</p>
                                    
                <div class="row">
                    <div class="col-sm"><p style="margin: 0; font-size: 10px">Key</p></div>
                    <div class="col-sm"><p style="margin: 0; font-size: 10px">Value</p></div>
                </div>
                            
                <ul class="list-group" style="height: 50%;">
                    <li v-if="metadataList.length == 0" class="list-group-item meta-item">
                        <i>No items in metadata.</i>
                    </li>
                    <li v-for="object in metadataList" class="list-group-item meta-item">
                        <div class="row">
                                   
                            <div class="col-sm">
                                <input v-model="object.key" type="text" class="meta-input" placeholder="Key">
                            </div>
                                                
                            <div class="col-sm">
                                <input v-model="object.value" type="text" class="meta-input" placeholder="Value">
                            </div>
                        </div>
                    </li>
                </ul>
            </div>
        `,
        watch: {
        },
        methods: {
            export: function () {

                let metadata = {};

                this.metadataList.forEach(object => {
                    if (object.key.length > 0) {
                        if (!isNaN(object.value))
                            metadata[object.key] = parseInt(object.value);
                        else if (object.value.toLowerCase() === "true" || object.value.toLowerCase() === "false")
                            metadata[object.key] = (object.value.toLowerCase() === 'true');
                        else
                            metadata[object.key] = object.value;
                    }
                });
                console.log(metadata);
                return metadata;
            },
            isJsonString: function (string) {
                try {
                    JSON.parse(string);
                } catch (e) {
                    return false;
                }

                return string;
            },
            createMetadata: function () {
                this.metadataList.push({key: "", value: ""})
            }
        },
        created() {
            console.log(this.metadata);
            for (var key in this.metadata) {
                if (!this.metadata.hasOwnProperty(key)) continue;

                let value = this.metadata[key];
                this.metadataList.push({key: key, value: value.toString()})

            }
        }
    });
});
