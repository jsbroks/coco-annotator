/**
 * Eraser Functions
 *
 * @author Justin Brooks
 */
define("eraserTool", ["paper"], function (paper) {



    return {
        initTool: function (eraser) {

            eraser.brush = new paper.Path.Circle({
                strokeColor: eraser.pathOptions.strokeColor,
                strokeWidth: eraser.pathOptions.strokeWidth,
                radius: eraser.pathOptions.radius
            });
            eraser.brush.visible = false;
        },
        moveBrush: function (point, brush) {
            brush.bringToFront();
            brush.position = point;
        },
        erasePath: function (vue, path, id) {
            let category = vue.getCategory(vue.current.category);

            if (vue.eraser.brush.intersects(path)) {

                let tempPath = path.subtract(vue.eraser.brush);
                tempPath.flatten(vue.eraser.simplify);

                category.getAnnotation(id).setCompoundPath(tempPath);
                path = tempPath;

                if (path.constructor.name === "Path") {
                    if (path.area < vue.eraser.minimumArea)
                        category.getAnnotation(id).createCompoundPath();
                }

                if (path.constructor.name === "CompoundPath") {
                    for (let i = 0; i < path.children.length; i++) {
                        let pathTemp = path.children[i];
                        if (pathTemp.area < vue.eraser.minimumArea) pathTemp.remove();
                    }
                }
            }
        },
        erase: function (event, vue) {
            let category = vue.getCategory(vue.current.category);

            if (category == null) return;
            if (category.group == null) return;
            for (let i = 0; i < category.group.children.length; i++) {
                let path = category.group.children[i];

                if (path.area === 0) continue;
                if (!path.visible) continue;

                this.erasePath(vue, path, i)
            }
        },
        onMouseDown: function (event, canvas, hitOptions) {

        },
        onMouseDrag: function (event, vue) {
            this.moveBrush(event.point, vue.eraser.brush);
            this.erase(event, vue);
        },
        onMouseMove: function (event, brush) {
            this.moveBrush(event.point, brush)
        },
    };
});