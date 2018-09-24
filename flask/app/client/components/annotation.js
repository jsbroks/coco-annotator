define(['Vue', 'paper', 'axios'], function (Vue, paper, axios) {

    Vue.component('annotation', {
        props: {
            annotation: {
                type: Object,
                required: true,
            },
            index: {
                type: Number,
                required: true,
            },
            current: {
                type: Number,
                required: true,
            },
            hover: {
                type: Number,
                required: true,
            },
            opacity: {
                type: Number,
                required: true
            }
        },
        data: function () {
            return {
                isVisible: true,
                color: this.annotation.color,
                compoundPath: null,
                isEmpty: true // Cannot make this a compute because vue can't track it.
            }
        },
        template: `
            <div>
                <li class="list-group-item btn btn-link btn-sm text-left"
                    :style="{ 'background-color': backgroundColor, color: 'white' }">
                    <div @click="isVisible = !isVisible">
                        <i v-if="isVisible" class="fa fa-eye annotation-icon"
                            :style="{ float: 'left', 'padding-right': '10px', color: color }"></i>
                        <i v-else class="fa fa-eye-slash annotation-icon"
                            style="float: left; padding-right: 10px; color: gray"></i>
                    </div>
             
                    <a @click="onAnnotationClick"
                        :style="{ float: 'left', width: '70%', color: isVisible ? 'white' : 'gray' }">
                        {{ index + 1 }} {{ annotation.name }}
                        <i v-if="isEmpty" style="padding-left: 5px; color: lightgray">(Empty)</i>
                        <i v-else style="padding-left: 5px; color: lightgray">(id: {{ annotation.id }})</i>
                    </a>
                    <i class="fa fa-gear annotation-icon" style="float:right" data-toggle="modal"
                        :data-target="'#annotationSettings' + annotation.id"></i>
                    <i @click="deleteAnnotation" class="fa fa-trash-o annotation-icon" style="float:right"></i>
            
                </li>
                <div class="modal fade" tabindex="-1" role="dialog" :id="'annotationSettings' + annotation.id">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">{{ index + 1 }} <i style="color: darkgray">(id: {{ annotation.id }})</i></h5>
                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body">
                                <form>
                                    <div class="form-group row">
                                        <label class="col-sm-2 col-form-label">Color</label>
                                        <div class="col-sm-9">
                                            <input v-model="color" type="color" class="form-control">
                                        </div>
                                    </div>
                                </form>  
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `,
        methods: {
            initAnnotation: function () {
                this.createCompoundPath(this.annotation.paper_object, this.annotation.segmentation);
            },

            createCompoundPath: function (json, segments) {
                json = json || null;
                segments = segments || null;

                if (json != null) {
                    if (json.length !== 2) {
                        json = null;
                    }
                }
                if (segments != null) {
                    if (segments.length === 0) {
                        segments = null;
                    }
                }

                this.compoundPath = new paper.CompoundPath();
                if (json != null) {
                    this.compoundPath.importJSON(this.annotation.paper_object);
                } else if (segments != null) {

                    let center = new paper.Point(this.annotation.width/2, this.annotation.height/2);

                    for (let i = 0; i < segments.length; i++) {
                        let polygon = segments[i];
                        let path = new paper.Path();

                        for (let j = 0; j < polygon.length; j+=2) {
                            let point = new paper.Point(polygon[j],  polygon[j+1]);
                            path.add(point.subtract(center))
                        }
                        path.closePath();
                        this.compoundPath.addChild(path)
                    }
                }

                this.setColor();
                this.compoundPath.data.annotationId = this.index;
                this.$parent.group.addChild(this.compoundPath);

                this.isEmpty = this.compoundPath.isEmpty();
            },

            deleteAnnotation: function () {
                axios.delete('/api/annotation/' + this.annotation.id).then(reponse => {
                    this.$parent.category.annotations.splice(this.index, 1);
                    if (this.compoundPath != null)
                        this.compoundPath.remove();
                });
            },

            onAnnotationClick: function (event) {
                if (this.isVisible) {
                    this.$emit('click', event)
                }
            },

            getCompoundPath: function () {
                if (this.compoundPath == null) {
                    this.createCompoundPath()
                }
                this.isEmpty = this.compoundPath.isEmpty();
                return this.compoundPath;
            },
            setCompoundPath: function (compoundPath) {
                this.compoundPath.remove();
                this.compoundPath = compoundPath;

                this.isEmpty = this.compoundPath.isEmpty();
            },
            setColor: function () {
                if (this.compoundPath == null) return;

                this.compoundPath.fillColor = this.color;
                // Strokes case lag, issue #39
                // let h = Math.round(this.compoundPath.fillColor.hue);
                // let l = Math.round((this.compoundPath.fillColor.lightness - 0.2) * 100);
                // let s = Math.round(this.compoundPath.fillColor.saturation * 100);
                // this.compoundPath.strokeColor = 'hsl(' + h + ',' + s + '%,' + l + '%)'
            },
            export: function () {
                let annotationData = {
                    id: this.annotation.id,
                    color: this.color,
                    metadata: {}
                };

                let json = this.compoundPath.exportJSON({asString: false, precision: 2});
                if (this.annotation.paper_object !== json) {
                    annotationData.compoundPath = json
                }

                return annotationData;
            },
        },
        watch: {
            color: function (newColor, oldColor) {
                if (this.compoundPath != null) {
                    this.setColor();
                }
            },
            isVisible: function (newVisible, oldVisible) {
                if (this.compoundPath != null) {
                    this.compoundPath.visible = newVisible;
                }
            },
        },
        computed: {
            isCurrent: function () {
                return this.index === this.current;
            },
            isHover: function () {
                return this.index === this.hover;
            },
            backgroundColor: function () {
                if (this.isHover)
                    return '#646c82';

                if (this.isCurrent)
                    return '#4b624c';

                return 'inherit';
            },
        },
        created () {
        }
    });
});
