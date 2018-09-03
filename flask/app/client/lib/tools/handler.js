/**
 * Tools Functions
 *
 * @author Justin Brooks
 */
define("tools", [
    "paper",
    "polygonTool",
    "selectTool",
    "eraserTool"
], function (paper,
             polygonTool,
             selectTool,
             eraserTool) {

    return {
        vue: null,
        initTools: function (vue) {
            this.vue = vue;

            vue.tool = new paper.Tool();
            vue.polygon.path = new paper.Path(vue.polygon.pathOptions);
            vue.polygon.bush = new paper.Path.Circle({
                strokeColor: ''
            });

            vue.polygon.toggleGuidance = polygonTool.toggleGuidance;

            vue.tool.onMouseDrag = (event) => {
                if (vue.activeTool.toLowerCase() === 'polygon')
                    polygonTool.onMouseDrag(event, vue.polygon, vue.compoundPath);

                if (vue.activeTool.toLowerCase() === 'select')
                    selectTool.onMouseDrag(event);

            };

            vue.tool.onMouseDown = (event) => {
                if (vue.activeTool.toLowerCase() === 'polygon')
                    polygonTool.onMouseDown(event, vue.polygon, vue.compoundPath);

                if (vue.activeTool.toLowerCase() === 'select')
                    selectTool.onMouseDown(event, vue.paper);
            };

            vue.tool.onMouseMove = (event) => {
                if (vue.activeTool.toLowerCase() === 'polygon')
                    polygonTool.onMouseMove(event, vue.polygon);

                if (vue.activeTool.toLowerCase() === 'select')
                    selectTool.onMouseMove(event, vue.paper, vue.hover);

                if (vue.activeTool.toLowerCase() === 'eraser')
                    eraserTool.onMouseMove(event, vue.paper, vue.eraser);
            };

            vue.tool.onMouseUp = (event) => {
                if (vue.activeTool.toLowerCase() === 'polygon')
                    polygonTool.onMouseMove(event, vue.polygon);

                if (vue.activeTool.toLowerCase() === 'select')
                    selectTool.onMouseUp(event)
            };
        }
    };
});