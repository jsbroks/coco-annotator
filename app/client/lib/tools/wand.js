/**
 * Wand Functions
 *
 * @author Justin Brooks
 */
define("wandTool", ["paper", "magicWand"], function(paper) {

    return {
        tempCtx: null,
        imageInfo: {},
        mask: null,
        initTool: function(image) {
            let raster = image.raster;
            this.imageInfo.width = raster.width;
            this.imageInfo.height = raster.height;
            this.imageInfo.bytes = 4;

            // Create a copy of image data
            let tempCtx = document.createElement("canvas").getContext("2d");
            tempCtx.canvas.width = raster.width;
            tempCtx.canvas.height = raster.height;
            tempCtx.drawImage(raster.image, 0, 0);

            this.imageInfo.data = tempCtx.getImageData(0, 0, raster.width, raster.height);
        },
        // Modified: https://github.com/Hitachi-Automotive-And-Industry-Lab/semantic-segmentation-editor/blob/master/imports/editor/2d/tools/SseFloodTool.js
        flood: function (x, y, thr, rad, simplify) {
            let image = {
                data: this.imageInfo.data.data,
                width: this.imageInfo.width,
                height: this.imageInfo.height,
                bytes: this.imageInfo.bytes
            };

            let mask = MagicWand.floodFill(image, x, y, thr);
            rad = rad < 1 ? 1 : Math.abs(rad);
            mask = MagicWand.gaussBlurOnlyBorder(mask, rad);

            let contours = MagicWand.traceContours(mask).filter(x => !x.inner);
            contours = MagicWand.simplifyContours(contours, simplify, 30);

            if (contours[0]) {

                let centerX = image.width/2;
                let centerY = image.height/2;

                let points = contours[0].points;
                points = points.map(pt => ({x: pt.x + 0.5 - centerX, y: pt.y - centerY}));

                let polygon = new paper.Path(points);
                polygon.closed = true;

                return polygon;
            }
            return null;
        },

        onMouseDown: function (event, vue) {

            let wand = vue.wand;
            let compound = vue.compoundPath;

            let x = Math.round((this.imageInfo.width / 2) + event.point.x);
            let y = Math.round((this.imageInfo.height / 2) + event.point.y);

            if (x > this.imageInfo.width
                || y > this.imageInfo.height
                || x < 0
                || y < 0) {
                return;
            }

            let path = this.flood(x, y, wand.threshold, wand.blur, wand.simplify);

            if (event.modifiers.shift) {
                vue.setCompoundPath(compound.subtract(path));
            } else {
                vue.setCompoundPath(compound.unite(path));
            }

            if (path != null) path.remove();

        },

        onMouseDrag: function (event, vue) {
            this.onMouseDown(event, vue)
        }
    };
});