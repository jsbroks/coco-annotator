<template>
  <div>
    <li 
      class="list-group-item btn btn-link btn-sm text-left"
      :style="{ 'background-color': backgroundColor, color: 'white' }"
    >
      <div @click="isVisible = !isVisible">
        
        <i 
          v-if="isVisible" 
          class="fa fa-eye annotation-icon"
          :style="{ float: 'left', 'padding-right': '10px', color: color }"
        />

        <i 
          v-else 
          class="fa fa-eye-slash annotation-icon"
          style="float: left; padding-right: 10px; color: gray"
        />

      </div>
             
      <a 
        @click="onAnnotationClick"
        :style="{ float: 'left', width: '70%', color: isVisible ? 'white' : 'gray' }"
      >
        {{ index + 1 }} {{ annotation.name }}
        
        <i 
          v-if="isEmpty" 
          style="padding-left: 5px; color: lightgray"
        >(Empty)</i>

        <i 
          v-else 
          style="padding-left: 5px; color: lightgray"
        >(id: {{ annotation.id }})</i>

      </a>
      <i 
        class="fa fa-gear annotation-icon" 
        style="float:right" 
        data-toggle="modal"
        :data-target="'#annotationSettings' + annotation.id"
      />
      <i 
        @click="deleteAnnotation" 
        class="fa fa-trash-o annotation-icon" 
        style="float:right"
      />
            
    </li>
  </div>
</template>

<script>
import paper from "paper";
import axios from "axios";

export default {
  name: "Annotaiton",
  props: {
    annotation: {
      type: Object,
      required: true
    },
    index: {
      type: Number,
      required: true
    },
    current: {
      type: Number,
      required: true
    },
    hover: {
      type: Number,
      required: true
    },
    opacity: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      isVisible: true,
      color: this.annotation.color,
      compoundPath: null,
      metadata: [],
      isEmpty: true
    };
  },
  methods: {
    initAnnotation() {
      this.createCompoundPath(
        this.annotation.paper_object,
        this.annotation.segmentation
      );
    },
    createCompoundPath(json, segments) {
      json = json || null;
      segments = segments || null;

      // Validate json
      if (json != null) {
        if (json.length !== 2) {
          json = null;
        }
      }

      // Validate segments
      if (segments != null) {
        if (segments.length === 0) {
          segments = null;
        }
      }

      if (this.compoundPath != null) this.compoundPath.remove();

      // Create new compoundpath
      this.compoundPath = new paper.CompoundPath();

      if (json != null) {
        // Import data directroy from paperjs object
        this.compoundPath.importJSON(this.annotation.paper_object);
      } else if (segments != null) {
        // Load segments input compound path
        let center = new paper.Point(
          this.annotation.width / 2,
          this.annotation.height / 2
        );

        for (let i = 0; i < segments.length; i++) {
          let polygon = segments[i];
          let path = new paper.Path();

          for (let j = 0; j < polygon.length; j += 2) {
            let point = new paper.Point(polygon[j], polygon[j + 1]);
            path.add(point.subtract(center));
          }
          path.closePath();
          this.compoundPath.addChild(path);
        }
      }

      this.setColor();
      this.compoundPath.data.annotationId = this.index;
      this.$parent.group.addChild(this.compoundPath);

      this.isEmpty = this.compoundPath.isEmpty();
    },
    deleteAnnotation() {
      axios.delete("/api/annotation/" + this.annotation.id).then(() => {
        this.$parent.category.annotations.splice(this.index, 1);
        if (this.compoundPath != null) this.compoundPath.remove();
      });
    },
    onAnnotationClick() {
      if (this.isVisible) {
        this.$emit("click", event);
      }
    },
    getCompoundPath() {
      if (this.compoundPath == null) {
        this.createCompoundPath();
      }
      this.isEmpty = this.compoundPath.isEmpty();
      return this.compoundPath;
    },
    setCompoundPath(compoundPath) {
      this.compoundPath.remove();
      this.compoundPath = compoundPath;

      this.isEmpty = this.compoundPath.isEmpty();
    },
    setColor() {
      if (this.compoundPath == null) return;

      this.compoundPath.fillColor = this.color;
      // let h = Math.round(this.compoundPath.fillColor.hue);
      // let l = Math.round((this.compoundPath.fillColor.lightness - 0.2) * 100);
      // let s = Math.round(this.compoundPath.fillColor.saturation * 100);
      // this.compoundPath.strokeColor = 'hsl(' + h + ',' + s + '%,' + l + '%)';
    },
    export() {
      if (this.compoundPath == null) this.createCompoundPath();

      let annotationData = {
        id: this.annotation.id,
        color: this.color,
        metadata: this.$refs.metadata.export()
      };

      let json = this.compoundPath.exportJSON({
        asString: false,
        precision: 1
      });
      if (this.annotation.paper_object !== json) {
        annotationData.compoundPath = json;
      }

      return annotationData;
    }
  },
  watch: {
    color() {
      this.setColor();
    },
    isVisible(newVisible) {
      if (this.compoundPath == null) return;

      this.compoundPath.visible = newVisible;
    }
  },
  computed: {
    isCurrent() {
      return this.index === this.current;
    },
    isHover() {
      return this.index === this.hover;
    },
    backgroundColor() {
      if (this.isHover) return "#646c82";

      if (this.isCurrent) return "#4b624c";

      return "inherit";
    }
  }
};
</script>

<style scoped>
.list-group-item {
  height: 22px;
  font-size: 13px;
  padding: 2px;
  background-color: #4b5162;
}
.annotation-icon {
  margin: 0;
  padding: 3px;
}
</style>
