requirejs.config({
    baseUrl: '/client/lib/',
    paths: {

        // Libraries
        Vue: 'vue-2.5.17',

        paper: 'paper-0.11.5',
        axios: 'axios-0.18.0',
        magicWand: 'magic-wand',

        // Tools
        polygonTool: 'tools/polygon',
        selectTool: 'tools/select',
        eraserTool: 'tools/eraser',
        wandTool: 'tools/wand',
        tools: 'tools/handler',

        // Components
        toolPanel: '../components/tool-panel',
        category: '../components/category',
        annotation: '../components/annotation',
        asyncStatus: '../components/async-status',
        pagination: '../components/pagination',

        imageCard: '../components/image-card',
        datasetCard: '../components/dataset-card',
        categoryCard: '../components/category-card',

        // Pages
        annotator: '../app/annotator',
        images: '../app/images',
        datasets: '../app/datasets',
        categories: '../app/categories',
        undo: '../app/undo',
    },
    findNestedDependencies: true,
});
