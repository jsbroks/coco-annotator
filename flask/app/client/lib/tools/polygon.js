/**
 * Polygon Functions
 *
 * @author Justin Brooks
 */
define("polygonTool", ["paper", "simplify"], function(paper, simplify) {

    return {
        /**
         * Completes polygon if click event is within distanced.
         *
         * @param {object} polygon - Polygon tool from main vue instance
         * @param {int} minLength - Required minimal points before auto complete
         * @param {object} compound - Paper CompoundPath to add polygon too
         * @returns {boolean} - Successfully completed
         */
        autoComplete: function (polygon, minLength, compound) {
            if (polygon.path == null) return false;
            if (polygon.path.segments.length < minLength) return false;

            let last = polygon.path.lastSegment.point;
            let first = polygon.path.firstSegment.point;

            if (last.isClose(first, polygon.completeDistance)) {
                return this.complete(polygon, compound);
            }

            return false;
        },

        /**
         * Closes current polygon
         *
         * @param {object} polygon - Polygon to close
         * @param {object} compound - Paper CompoundPath to add polygon too
         */
        complete: function (polygon, compound) {
            if (polygon.path == null) return false;
            if (compound == null) return false;

            polygon.path.closePath();
            if (polygon.simplify > 0) {
                let points = [];

                polygon.path.segments.forEach(seg => { points.push({x: seg.point.x, y: seg.point.y})});
                let previous = points.length;
                points = simplify(points, polygon.simplify, true);

                console.log("Reduced by "  + (previous - points.length) + " points.");
                polygon.path.remove();
                polygon.path = new paper.Path(points);
            }



            for (let i = 0 ; i < compound.children.length; i++) {

                let path = compound.children[i];
                let crossings = path.getCrossings(polygon.path);

                if (crossings.length > 1) {
                    let newPath = path.unite(polygon.path);
                    polygon.path.remove();
                    compound.children[i].remove();
                    polygon.path = newPath;
                }
            }

            compound.addChild(polygon.path);
            polygon.path = null;

            return true;
        },

        /**
         * Add points to polygon, auto complete if distance is close
         *
         * @param {event} event - Paper event
         * @param {object} polygon - Polygon to modify
         * @param {object} compound - Paper CompoundPath to add polygon too if completed
         */
        onMouseDown: function (event, polygon, compound) {

            if (polygon.path == null) {
                polygon.path = this._createPath(polygon.pathOptions);
            }

            polygon.path.add(event.point);
            if (this.autoComplete(polygon, 3, compound)) return;
            if (polygon.guidance) polygon.path.add(event.point);
        },

        /**
         * Nothing
         *
         * @param {event} event - Paper event
         * @param {object} polygon - Polygon to modify
         */
        onMouseUp: function (event, polygon) {

        },

        /**
         * Event handler for when mouse is dragged, on canvas, well
         * polygon tool is active.
         *
         * @param {event} event - Paper event
         * @param {object} polygon - Polygon to modify
         * @param {object} compound - Paper CompoundPath to add polygon too if completed
         */
        onMouseDrag: function (event, polygon, compound) {
            if (polygon.path == null) { return }
            polygon.path.add(event.point);
            this.autoComplete(polygon, 30, compound);
        },

        /**
         * Event handler for when mouse is moved, on canvas, well
         * polygon tool is active.
         *
         * @param {event} event - Paper event
         * @param {object} polygon - Polygon to modify
         */
        onMouseMove: function (event, polygon) {
            if (polygon.path == null) return;
            if (!polygon.guidance) return;
            if (polygon.path.segments.length === 0) return;

            polygon.path.removeSegment(polygon.path.segments.length - 1);
            polygon.path.add(event.point)
        },

        /**
         * Toggle guidance, which will remove the last segmentation
         * placed by hovering mouse
         *
         * @param {object} polygon - Polygon to modify
         */
        toggleGuidance: function (polygon) {

            if (polygon.guidance && polygon.path.length > 1) {
                polygon.path.removeSegment(polygon.path.segments.length - 1);
            }

            polygon.guidance = !polygon.guidance;

        },

        _createPath: function (options) {
            return new paper.Path(options);
        },
    };
});