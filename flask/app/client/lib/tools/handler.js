/**
 * Tools Functions
 *
 * @author Justin Brooks
 */
define("tools", [
    "paper",
    "polygonTool",
    "selectTool",
    "eraserTool",
    "wandTool"
], function (paper,
             polygonTool,
             selectTool,
             eraserTool,
             wandTool) {

    return {
        vue: null,
        initTools: function (vue) {
            this.vue = vue;

            vue.tool = new paper.Tool();
            vue.polygon.path = new paper.Path(vue.polygon.pathOptions);
            vue.polygon.bush = new paper.Path.Circle({
                strokeColor: ''
            });

            wandTool.initTool(vue.image);

            vue.polygon.toggleGuidance = polygonTool.toggleGuidance;

            vue.tool.onMouseDrag = (event) => {
                if (vue.activeTool.toLowerCase() === 'polygon')
                    polygonTool.onMouseDrag(event, vue.polygon, vue.compoundPath);

                if (vue.activeTool.toLowerCase() === 'select')
                    selectTool.onMouseDrag(event);

                if (vue.activeTool.toLowerCase() === 'wand')
                    wandTool.onMouseDrag(event, vue);
            };

            vue.tool.onMouseDown = (event) => {
                if (vue.activeTool.toLowerCase() === 'polygon')
                    polygonTool.onMouseDown(event, vue.polygon, vue.compoundPath);

                if (vue.activeTool.toLowerCase() === 'select')
                    selectTool.onMouseDown(event, vue.paper);

                if (vue.activeTool.toLowerCase() === 'wand')
                    wandTool.onMouseDown(event, vue);
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