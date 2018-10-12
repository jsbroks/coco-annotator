define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('metadata', {
        props: {
            metadata: {
                type: Object,
                required: false
            },
            title: {
                type: String,
                required: false
            },
            keyName: {
                type: String,
                required: false
            },
            valueName: {
                type: String,
                required: false
            },
        },
        data: function () {
            return {
                metadataList: [],
                titleName: "Metadata",
                titleKey: "Key",
                titleValue: "Value"
            }
        },
        template: `
            <div>
                <i class="fa fa-plus" style="float: right; margin: 0 4px; color: green"
                    @click="createMetadata"></i>
                    
                <p style="margin: 0">{{ this.titleName }}</p>
                                    
                <div class="row">
                    <div class="col-sm"><p style="margin: 0; font-size: 10px">{{titleKey}}</p></div>
                    <div class="col-sm"><p style="margin: 0; font-size: 10px">{{titleValue}}</p></div>
                </div>
                            
                <ul class="list-group" style="height: 50%;">
                    <li v-if="metadataList.length == 0" class="list-group-item meta-item">
                        <i>No items in metadata.</i>
                    </li>
                    <li v-for="object in metadataList" class="list-group-item meta-item">
                        <div class="row">
                                   
                            <div class="col-sm">
                                <input v-model="object.key" type="text" class="meta-input" :placeholder="titleKey">
                            </div>
                                                
                            <div class="col-sm">
                                <input v-model="object.value" type="text" class="meta-input" :placeholder="titleValue">
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

                return metadata;
            },
            createMetadata: function () {
                this.metadataList.push({key: "", value: ""})
            }
        },
        created() {

            if (this.title != null) this.titleName = this.title;
            if (this.valueName != null) this.titleValue = this.valueName;
            if (this.keyName != null) this.titleKey = this.keyName;
            
            if (this.metadata != null) {
                for (var key in this.metadata) {
                    if (!this.metadata.hasOwnProperty(key)) continue;

                    let value = this.metadata[key];
                    this.metadataList.push({key: key, value: value.toString()})

                }
            }
        }
    });
});
