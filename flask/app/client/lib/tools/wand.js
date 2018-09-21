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
            console.log(image);
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
        flood: function (x, y, thr, rad) {

            let mask = MagicWand.floodFill(this.imageInfo, x, y, thr);
            mask = MagicWand.gaussBlurOnlyBorder(mask, rad);

            let contours = MagicWand.traceContours(mask).filter(x => !x.inner);

            console.log(contours);

            if (contours[0]) {
                let points = contours[0].points;
                points.map(pt => ({x: pt.x + .5, y: pt.y + .5}));
                // SIMPLY

                let polygon = new paper.Path(points, {fillColor: 'black'});


            }
        },
        
        onMouseDown: function (event, wand, compoundPath, paper) {

            let x = Math.round((this.imageInfo.width / 2) + event.point.x);
            let y = Math.round((this.imageInfo.height / 2) + event.point.y);

            if (x > this.imageInfo.width
                || y > this.imageInfo.height
                || x < 0
                || y < 0) {
                return;
            }
            console.log(MagicWand);
            console.log(x, y, this.imageInfo);
            this.flood(x, y, wand.threshold, wand.blur);
        },

        onMouseDrag: function (event, wand, compoundPath, imageRaster) {

        }
    };
});