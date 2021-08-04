//Loading a JavaScript library from a CDN
importScripts("https://cdnjs.cloudflare.com/ajax/libs/paper.js/0.12.15/paper-full.js");


onmessage = function(e) {
    console.log('Worker: Message received from main script');
    
    // Get received data 
    let x  = e.data[1];
    let y  = e.data[2];
    let height  = e.data[3];
    let width  = e.data[4];

    console.log("height", height, "width", width)

    // Create a scope to avoid the error due to 'project' is null
    let scope = new paper.PaperScope();
    scope.setup(new paper.Size(width, height));

    //recreate the paperjs object
    let path = new paper.CompoundPath(); 
    path.importJSON(e.data[0]);

    //inintiate a binary mask full of zeros
    let mask = Array.from(Array(height), () => new Array(width).fill(0));

    //register the pixels who belong to the current polygon path
    for(var i = 0; i < height; i++) {
        for(var j = 0; j < width; j++) {
            if (path.contains( new paper.Point(i + x, j + y))) {
                mask[i][j] = 1;
            }
        }
    }

    console.log('Worker: Posting message back to main script');
    this.postMessage(mask);
  }

  onerror = event => {
    console.error(event.message)
  }
