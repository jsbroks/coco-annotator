/**
 * selectTool Functions
 *
 * @author Justin Brooks
 */
define("selectTool", ["paper"], function (paper) {

    return {
        segment: null,
        segmentFound: false,
        movePath: false,
        hitOptions: {
            segments: true,
            stroke: true,
            fill: false,
            class: paper.Path,
            tolerance: 2
        },
        onMouseUp: function (event) {
        },
        onMouseDown: function (event, canvas, hitOptions) {
            hitOptions = hitOptions || this.hitOptions;
            this.segmentFound = false;
            let hitResult = canvas.project.hitTest(event.point, hitOptions);

            if (!hitResult)
                return;

            if (event.modifiers.shift) {
                if (hitResult.type === 'segment') {
                    hitResult.segment.remove();
                }
                return;
            }

            this.path = hitResult.item;

            if (hitResult.type === 'segment') {
                this.segment = hitResult.segment;
            } else if (hitResult.type === 'stroke') {
                let location = hitResult.location;
                this.segment = this.path.insert(location.index + 1, event.point);
            }
            this.segmentFound = true;
        },

        onMouseDrag: function (event) {
            if (this.segment && this.segmentFound) {
                this.segment.point = event.point;
            }
        },

        onMouseMove: function (event, canvas, hover) {
            canvas.project.activeLayer.selected = false;
            if (event.item
                && event.item.opacity !== 0
                && event.item.data.hasOwnProperty('categoryId')) {
                let item = event.item;
                hover.category = item.data.categoryId;

                if (item.hasChildren()) {
                    // Find child that contains clicked point
                    for (let i = 0; i < item.children.length; i++) {
                        let child = item.children[i];
                        if (child.opacity !== 0
                            && child.contains(event.point)
                            && child.data.hasOwnProperty('annotationId')) {

                            // Child with clicked point
                            child.selected = true;
                            hover.annotation = child.data.annotationId;
                            return;
                        }
                    }
                }
            } else {
                hover.category = -1;
                hover.annotation = -1;
            }
        },
    };
});