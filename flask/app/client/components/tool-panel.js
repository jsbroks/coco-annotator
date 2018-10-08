define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('tool-panel', {
        model: {
            prop: 'selected',
            event: 'change'
        },
        props: {
            selected: {
                type: String,
                required: true
            },
            current: {
                type: Object,
                required: true
            }
        },
        data: function () {
            return {
                lastSelected: 'Selected',
                activeColor: '#2ecc71',
                tools: {
                    Select: {
                        class: 'fa fa-hand-pointer-o fa-x',
                        description: 'Select (S)',
                        color: 'white',
                        hr: true
                    },
                    // Move: {class: 'fa fa-arrows fa-x', color: 'white'},
                    Polygon: {
                        class: 'fa fa-pencil fa-x',
                        description: 'Polygon/Lasso (P)',
                        disabled: true,
                        color: 'white',
                    },
                    // Points: {class: 'fa fa-dot-circle-o fa-x', description: 'Key Points', color: 'white'},
                    // Bush: {class: 'fa fa-paint-brush fa-x', color: 'white'},
                    Wand: {
                        class: 'fa fa-magic fa-x',
                        disabled: true,
                        color: 'white',
                        description: 'Magic Wand (W)',
                        hr: true
                    },
                    Eraser: {
                        class: 'fa fa-eraser fa-x',
                        color: 'white',
                        hr: true
                    },
                    // Undo: {class: 'fa fa-undo fa-x', color: 'white', hr: true},

                    Fit: {
                        class: 'fa fa-align-center fa-x',
                        description: 'Center Image (C)',
                        color: 'white'
                    },
                    HideRight: {
                        class: 'fa fa-sign-in fa-x',
                        description: 'Toggle Right Panel',
                        color: 'white',
                        hr: true
                    },

                    Save: {
                        class: 'fa fa-floppy-o fa-x',
                        color: 'white',
                        description: 'Save (Ctrl+S)'
                    },
                    Download: {
                        class: 'fa fa-download fa-x',
                        description: 'Download Image and Coco (Ctrl+D)',
                        color: 'white'
                    },
                    Delete: {
                        class: 'fa fa-trash-o fa-x',
                        description: 'Delete Image and Annotations',
                        color: 'white'
                    },
                    // Settings: {class: 'fa fa-gear fa-x', color: 'white'},
                    // Extra: {class: 'fa fa-ellipsis-h fa-x', color: 'white'},
                }
            }
        },
        template: `
            <div>
                <hr>
                <div v-for="key in Object.keys( tools )" class="tool">
            
                    <i :class="tools[key].class"
                        :id="key"
                        :style="{ color: tools[key].disabled ? 'gray' : tools[key].color }"
                        @click="click(key)"
                        aria-hidden="true"
                        data-toggle="tooltip"
                        :title="tools[key].description"
                        data-placement="auto"></i>
                    
                    <hr v-if="tools[key].hr">
                </div>
            </div>
        `,
        watch: {
            selected: function (newAction, oldAction) {

                if (this.tools[newAction].disabled) {
                    // Tool is disabled
                    this.$parent.activeTool = oldAction;
                    return;
                }

                this.lastSelected = oldAction;
                this.tools[oldAction].color = 'white';
                this.tools[newAction].color = this.activeColor;
            },
            current: function (newCurrent, oldCurrent) {
                this.setDisableStates(newCurrent)
            }
        },
        methods: {
            setDisableStates: function (current) {
                if (current == null || (current.category === -1 && current.annotation === -1)) {
                    this.tools.Polygon.disabled = true;
                    this.tools.Wand.disabled = true;

                    if (['Polygon', 'Wand'].indexOf(this.selected) >= 0)
                        this.$emit('change', this.lastSelected);
                } else {
                    this.tools.Polygon.disabled = false;
                    this.tools.Wand.disabled = false;
                }
            },
            click: function (action) {
                switch (action.toLowerCase()) {
                    case 'settings':
                        this.feedback(action);
                        break;

                    case 'save':
                        this.feedback(action);
                        this.$parent.save();
                        break;

                    case 'download':
                        this.feedback(action);
                        this.$parent.downloadCoco();
                        break;

                    case 'hideright':
                        this.hideRight(this.tools[action]);
                        break;

                    case 'fit':
                        this.feedback(action);
                        this.$parent.fit();
                        break;

                    case 'undo':
                        this.feedback(action);
                        break;

                    case 'delete':
                        this.feedback(action);
                        this.$parent.deleteImage();
                        break;

                    default:
                        if (!this.tools[action].disabled)
                            this.$emit('change', action)
                }
            },

            feedback: async function (tool) {
                this.tools[tool].color = this.activeColor;
                setTimeout(() => this.tools[tool].color = 'white', 300)
            },

            hideRight: function (tool) {
                if (this.$parent.panels.right.show) {
                    tool.color = this.activeColor;
                } else {
                    tool.color = 'white';
                }

                this.$parent.panels.right.show = !this.$parent.panels.right.show;
            }
        },
        created() {

            for (let key in this.tools) {
                if (!this.tools.hasOwnProperty(key)) continue;

                if (key === this.selected) {
                    this.tools[key].color = this.activeColor;
                } else {
                    this.tools[key].color = 'white';
                }

                if (!this.tools[key].hasOwnProperty('description')) {
                    this.tools[key].description = key;
                }
            }

        },
        mounted() {
            this.setDisableStates();
            $('[data-toggle="tooltip"]').tooltip();
        }
    });
});
