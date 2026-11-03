<template>
<div class="modal fade" tabindex="-1" role="dialog" id="exportWizard">
  <div class="modal-dialog wizard-dialog" role="document">
    <div class="modal-content text-start">
      <div class="modal-header">
        <h5 class="modal-title text-truncate">{{ selected.length ? $t('dataset.exportTitle', { name: exportDatasetNames.join(' + ') }) : $t('exportPick.title') }}</h5>
        <button
          type="button"
          class="btn-close"
          data-bs-dismiss="modal"
          aria-label="Close"
        ></button>
      </div>
      <div class="modal-body pt-2">
        <!-- step indicator -->
        <ol class="export-steps">
          <li
            v-for="(name, i) in exportStepNames"
            :key="name"
            :class="{
              active: exporting.step === i + 1,
              done: exporting.step > i + 1 && !stepSkipped(i + 1),
              skipped: stepSkipped(i + 1),
              disabled: !canGoToStep(i + 1)
            }"
            @click="goToStep(i + 1)"
          >
            <span class="step-dot">
              <i v-if="stepSkipped(i + 1)" class="fa fa-minus" />
              <i v-else-if="exporting.step > i + 1" class="fa fa-check" />
              <template v-else>{{ i + 1 }}</template>
            </span>
            <span class="step-name">{{ $t('exportSteps.' + name) }}</span>
          </li>
        </ol>

        <form @submit.prevent>
          <!-- step 1: datasets (several go into one file) -->
          <div v-show="exporting.step === 1">
            <div class="small text-muted mb-2">{{ $t('exportPick.hint') }}</div>
            <input
              v-if="list.length > 6"
              v-model="filter"
              class="form-control form-control-sm mb-2"
              :placeholder="$t('exportMerge.search')"
            />
            <div v-if="loading" class="text-muted small"><i class="fa fa-spinner fa-spin" /></div>
            <div v-else-if="!list.length" class="text-muted small">{{ $t('exportPick.none') }}</div>
            <div v-else class="pick-list">
              <label v-for="d in shownList" :key="d.id" class="pick-item">
                <input v-model="selected" type="checkbox" class="form-check-input m-0" :value="d.id" />
                <span class="text-truncate flex-grow-1">
                  <span v-if="selected[0] === d.id && selected.length > 1" class="badge text-bg-secondary me-1" :title="$t('exportPick.mainHint')">{{ $t('exportPick.main') }}</span>
                  {{ d.name }}
                </span>
                <span class="small text-muted text-nowrap">{{ $t('exportMerge.images', { n: d.images }) }}</span>
                <span v-if="mergeMismatch(d)" class="small text-warning-emphasis text-nowrap" :title="mergeMismatch(d)">
                  <i class="fa fa-exclamation-triangle" /> {{ $t('exportMerge.differs') }}
                </span>
              </label>
            </div>
            <div v-if="selected.length > 1" class="small mt-2">
              {{ $t('exportPick.summary', { n: selected.length, images: selectedImages }) }}
            </div>
          </div>

          <!-- step 1: format -->
          <div v-show="exporting.step === 2">
            <div class="form-label fw-semibold">{{ $t('yolo.format') }}</div>
            <div class="row g-2 mb-3">
              <div v-for="f in ['coco', 'yolo']" :key="f" class="col-6">
                <label class="choice-card" :class="{ selected: exporting.format === f }">
                  <input v-model="exporting.format" type="radio" name="exportFormat" :value="f" class="d-none" />
                  <span class="fw-semibold">{{ f.toUpperCase() }}</span>
                  <span class="small text-muted">{{ $t('exportSteps.formatHint.' + f) }}</span>
                </label>
              </div>
            </div>

            <template v-if="exporting.format === 'yolo'">
              <div class="form-label fw-semibold">{{ $t('yolo.task') }}</div>
              <div class="row g-2">
                <div v-for="t in exportYoloTasks" :key="t" class="col-6">
                  <label class="choice-card" :class="{ selected: exporting.yolo_task === t }">
                    <input v-model="exporting.yolo_task" type="radio" name="exportYoloTask" :value="t" class="d-none" />
                    <span class="fw-semibold">{{ $t('yolo.' + t) }}</span>
                    <span class="small text-muted">{{ $t('yolo.exportHint.' + t) }}</span>
                  </label>
                </div>
              </div>
              <div class="form-check d-flex align-items-center gap-2 ps-0 mt-3">
                <input
                  id="exportWithImages"
                  type="checkbox"
                  class="form-check-input m-0"
                  :checked="exportWithImages"
                  :disabled="exporting.yolo_task === 'classify'"
                  @change="exporting.with_images = $event.target.checked"
                />
                <label class="form-check-label mb-0" for="exportWithImages">{{ $t('yolo.withImages') }}</label>
              </div>
              <div v-if="exporting.yolo_task === 'classify'" class="form-text mt-0 ms-4">{{ $t('yolo.classifyImages') }}</div>
              <div class="form-text mt-2">
                <i class="fa fa-info-circle" />
                {{ $t('exportSteps.prefixExample', { image: exportExampleName.image, label: exportExampleName.label }) }}
              </div>

            </template>
            <div v-else class="form-check d-flex align-items-center gap-2 ps-0">
              <input
                id="exportCocoWithImages"
                type="checkbox"
                class="form-check-input m-0"
                :checked="exportWithImages"
                :disabled="!!exportAugmentPayload"
                @change="exporting.with_images = $event.target.checked"
              />
              <label class="form-check-label mb-0" for="exportCocoWithImages">{{ $t('exportSteps.cocoWithImages') }}</label>
            </div>

          </div>

          <!-- step 2: folder (YOLO) -->
          <div v-show="exporting.step === 3">
            <template v-if="exporting.format === 'yolo'">
              <label class="form-label fw-semibold mb-1" for="exportFolder">{{ $t('exportSteps.folder') }}</label>
              <input
                id="exportFolder"
                v-model="exporting.folder"
                class="form-control"
                :class="{ 'is-invalid': !exportFolderName }"
                maxlength="100"
                :placeholder="defaultExportFolder"
              />
              <div v-if="!exportFolderName" class="invalid-feedback">{{ $t('exportSteps.folderRequired') }}</div>
              <div v-else-if="exportFolderName !== exporting.folder.trim()" class="form-text">
                {{ $t('exportSteps.folderCleaned', { name: exportFolderName }) }}
              </div>
              <div class="form-text">{{ $t('exportSteps.folderHint') }}</div>
              <pre class="zip-tree small mb-0 mt-2">{{ exportTree }}</pre>
            </template>
            <div v-else class="text-muted small">{{ $t('exportSteps.folderCoco') }}</div>
          </div>

          <!-- step 3: categories -->
          <div v-show="exporting.step === 4">
            <ExportCategories
              v-model:order="exporting.order"
              v-model:selected="exporting.categories"
              :categories="exportCategoryList"
              :counts="exporting.counts && exporting.counts.categories"
              :yolo-task="exporting.format === 'yolo' ? exporting.yolo_task : null"
            />
            <div class="form-check d-flex align-items-center gap-2 ps-0 mt-3">
              <input id="exportWithEmpty" v-model="exporting.with_empty_images" type="checkbox" class="form-check-input m-0" />
              <label class="form-check-label mb-0" for="exportWithEmpty">{{ $t('dataset.exportWithNotAnnotatedImages') }}</label>
            </div>
            <div class="form-check d-flex align-items-center gap-2 ps-0 mt-2">
              <input id="exportOnlyApproved" v-model="exporting.only_approved" type="checkbox" class="form-check-input m-0" />
              <label class="form-check-label mb-0" for="exportOnlyApproved">{{ $t('review.onlyApproved') }}</label>
            </div>
          </div>

          <!-- step 4: split (of the original pictures) -->
          <div v-show="exporting.step === 5">
            <ExportSplit
              v-model:enabled="exporting.split_on"
              v-model:ratios="exporting.split"
              v-model:seed="exporting.seed"
              :image-count="exportImageCount"
              :yolo="exporting.format === 'yolo'"
            />
          </div>

          <!-- step 5: augmentation (of the training images, after the split) -->
          <div v-show="exporting.step === 6">
            <ExportAugment
              v-model="exporting.augment"
            :yolo="exporting.format === 'yolo'"
              :image-count="exportImageCount"
              :split-on="exporting.split_on"
              :split-sizes="exportSplitSizes"
            />
          </div>

          <!-- step 6: review -->
          <div v-show="exporting.step === 7">
            <div class="export-summary">
              <dl class="row small mb-0">
                <template v-if="merge.length">
                  <dt class="col-4">{{ $t('exportMerge.datasets') }}</dt>
                  <dd class="col-8">
                    {{ exportDatasetNames.join(' + ') }}
                    <a href="#" class="ms-1 small" @click.prevent="goToStep(2)">{{ $t('exportSteps.edit') }}</a>
                    <div class="text-muted">{{ $t('exportMerge.namesNote') }}</div>
                  </dd>
                </template>
                <dt class="col-4">{{ $t('yolo.format') }}</dt>
                <dd class="col-8">
                  {{ exporting.format.toUpperCase() }}
                  <template v-if="exporting.format === 'coco' && exportWithImages"> · {{ $t('exportSteps.withImages') }}</template>
                  <template v-if="exporting.format === 'yolo'">
                    · {{ $t('yolo.' + exporting.yolo_task) }}
                    <template v-if="exportWithImages"> · {{ $t('exportSteps.withImages') }}</template>
                    <div class="text-muted">
                      {{ $t('exportSteps.prefixSummary', { image: exportExampleName.image }) }}
                    </div>
                  </template>
                  <a href="#" class="ms-1 small" @click.prevent="goToStep(2)">{{ $t('exportSteps.edit') }}</a>
                </dd>
                <template v-if="exporting.format === 'yolo'">
                  <dt class="col-4">{{ $t('exportSteps.folder') }}</dt>
                  <dd class="col-8">
                    {{ exportFolderName }}/
                    <a href="#" class="ms-1 small" @click.prevent="goToStep(3)">{{ $t('exportSteps.edit') }}</a>
                  </dd>
                </template>
                <dt class="col-4">{{ $t('exportSteps.categories') }}</dt>
                <dd class="col-8">
                  {{ $t('exportSteps.categoryCount', { n: exportSelectedNames.length, names: exportSelectedNames.join($t('exportSteps.separator')) }) }}
                  <a href="#" class="ms-1 small" @click.prevent="goToStep(4)">{{ $t('exportSteps.edit') }}</a>
                  <div v-if="exporting.with_empty_images" class="text-muted">{{ $t('dataset.exportWithNotAnnotatedImages') }}</div>
                  <div v-if="exporting.only_approved" class="text-muted">{{ $t('review.onlyApproved') }}</div>
                </dd>
                <dt class="col-4">{{ $t('exportSteps.contents') }}</dt>
                <dd class="col-8">
                  <template v-if="exportImageCount == null"><i class="fa fa-spinner fa-spin" /></template>
                  <template v-else>
                    <template v-if="exporting.format === 'yolo' && exporting.yolo_task === 'classify'">
                      {{ $t('exportSteps.classifyCount', { images: exportImageCount }) }}
                    </template>
                    <template v-else>
                      {{ $t('exportSteps.contentCount', { images: exportImageCount, annotations: exportAnnotationCount }) }}
                    </template>
                    <div v-if="exportAugmentPayload" class="text-muted">
                      {{ $t('exportAugment.plus', { n: exportTotalImages - exportImageCount, total: exportTotalImages }) }}
                    </div>
                  </template>
                </dd>
                <dt class="col-4">{{ $t('exportSteps.split') }}</dt>
                <dd class="col-8">
                  <template v-if="exporting.split_on">
                    <span v-for="k in ['train', 'val', 'test']" :key="k" class="me-2">
                      {{ $t('exportSplit.' + k) }} {{ exporting.split[k] }}%
                      <span class="text-muted">({{ exportSplitSizes[k] }}<template v-if="exportAugCounts[k].extra"> + {{ $t('exportAugment.augShort', { n: exportAugCounts[k].extra }) }}</template>)</span>
                    </span>
                    <div class="text-muted">{{ $t('exportSplit.seed') }} {{ exporting.seed }}</div>
                  </template>
                  <template v-else>{{ $t('exportSteps.noSplit') }}</template>
                  <a href="#" class="ms-1 small" @click.prevent="goToStep(5)">{{ $t('exportSteps.edit') }}</a>
                </dd>
                <dt class="col-4">{{ $t('exportAugment.short') }}</dt>
                <dd class="col-8 mb-0">
                  <template v-if="exportAugmentPayload">
                    {{ $t(exporting.split_on && exportAugmentPayload.scope === 'train' ? 'exportAugment.summaryShortTrain' : 'exportAugment.summaryShort', { copies: exportAugmentPayload.copies, ops: exportAugmentNames }) }}
                  </template>
                  <template v-else>{{ $t('exportAugment.none') }}</template>
                  <a href="#" class="ms-1 small" @click.prevent="goToStep(6)">{{ $t('exportSteps.edit') }}</a>
                </dd>

              </dl>
            </div>
            <template v-if="exporting.format === 'yolo'">
              <div class="fw-semibold small mt-3 mb-1">{{ $t('exportSteps.zipContents') }}</div>
              <pre class="zip-tree small mb-0">{{ exportTree }}</pre>
              <div class="form-text">
                {{ $t('exportSteps.trainWith') }}
                <code>{{ exportTrainCommand }}</code>
              </div>
            </template>
            <div v-if="!exportReady" class="small text-danger mt-2">{{ $t('exportSteps.notReady') }}</div>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button
          v-if="exporting.step > 1"
          type="button"
          class="btn btn-outline-secondary me-auto"
          @click="stepBy(-1)"
        >
          <i class="fa fa-chevron-left" /> {{ $t('exportSteps.back') }}
        </button>
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
          {{ $t('dataset.close') }}
        </button>
        <button
          v-if="exporting.step < exportStepNames.length"
          type="button"
          class="btn btn-primary"
          :disabled="!canGoToStep(nextStep(1))"
          @click="stepBy(1)"
        >
          {{ $t('exportSteps.next') }} <i class="fa fa-chevron-right" />
        </button>
        <button
          v-else
          type="button"
          class="btn btn-primary"
          :disabled="!exportReady"
          @click="start"
        >
          <i class="fa fa-download" /> {{ $t('dataset.export') }}
        </button>
      </div>
    </div>
  </div>
</div>

</template>

<script>
import axios from "axios";
import { hideModal, showModal } from "@/libs/modal";
import Dataset from "@/models/datasets";
import ExportCategories from "@/components/ExportCategories.vue";
import ExportSplit, { splitSizes, splitValid } from "@/components/ExportSplit.vue";
import ExportAugment, { augmentPayload, augmentedCounts, defaultAugment, OPS as AUGMENT_OPS } from "@/components/ExportAugment.vue";

/**
 * Export wizard: datasets (several go into one file; the first ticked is
 * the main one, which keeps the export), format, folder, categories,
 * split, augmentation, review. Used on the datasets page and on a
 * dataset's page (opened with that dataset ticked).
 *
 *   <ExportWizard ref="exportWizard" @started="..." />
 *   this.$refs.exportWizard.open([datasetId])
 *
 * Emits "started" {datasetId, taskId, names} once the export task runs.
 */
export default {
  name: "ExportWizard",
  components: { ExportCategories, ExportSplit, ExportAugment },
  emits: ["started"],
  data() {
    return {
      list: [],
      loading: false,
      filter: "",
      // ticked datasets, in the order they were ticked (the first is the main one)
      selected: [],
      exporting: {
        categories: [],
        with_empty_images: false,
        order: [],
        counts: null,
        step: 1,
        only_approved: false,
        folder: "",
        split_on: false,
        split: { train: 80, val: 20, test: 0 },
        seed: 42,
        format: "coco",
        yolo_task: "detect",
        with_images: false,
        augment: defaultAugment()
      },
      // the main dataset whose task / name the format and folder came from
      defaultsFor: null,
      exportYoloTasks: ["detect", "segment", "obb", "pose", "classify", "semantic"],
      exportStepNames: ["datasets", "format", "folder", "categories", "split", "augment", "review"]
    };
  },
  computed: {
    mainId() {
      return this.selected[0] ?? null;
    },
    main() {
      return this.list.find(d => d.id === this.mainId) || null;
    },
    mainName() {
      return this.main ? this.main.name : "";
    },
    mainTask() {
      return this.main ? this.main.task || "" : "";
    },
    mainCategories() {
      return this.main ? this.main.categories : [];
    },
    /** the other ticked datasets, merged into the main one's export */
    merge() {
      return this.selected.slice(1);
    },
    exportDatasetNames() {
      return this.selected.map(id => (this.list.find(d => d.id === id) || {}).name).filter(Boolean);
    },
    selectedImages() {
      return this.list.filter(d => this.selected.includes(d.id)).reduce((n, d) => n + d.images, 0);
    },
    shownList() {
      const q = this.filter.trim().toLowerCase();
      return q ? this.list.filter(d => d.name.toLowerCase().includes(q) || this.selected.includes(d.id)) : this.list;
    },
    exportSplitValid() {
      return splitValid(this.exporting.split);
    },
    defaultExportFolder() {
      return this.cleanFolderName(this.mainName) || "dataset";
    },
    /** The folder name as the server will write it */
    exportFolderName() {
      return this.cleanFolderName(this.exporting.folder);
    },
    exportTrainCommand() {
      const task = this.exporting.yolo_task;
      const data = task === "classify" ? this.exportFolderName : "data.yaml";
      const model = { detect: "yolo26n.pt", segment: "yolo26n-seg.pt", obb: "yolo26n-obb.pt", pose: "yolo26n-pose.pt",
        classify: "yolo26n-cls.pt", semantic: "yolo26n-sem.pt" }[task];
      return `yolo ${task} train data=${data} model=${model}`;
    },
    /** classify always ships the images (they are the dataset) */
    exportWithImages() {
      // augmented pictures only exist in the export
      return (this.exporting.format === "yolo" && this.exporting.yolo_task === "classify")
        || this.exporting.with_images || !!this.exportAugmentPayload;
    },
    exportAugmentPayload() {
      return augmentPayload(this.exporting.augment);
    },
    exportAugmentNames() {
      const ops = (this.exportAugmentPayload && this.exportAugmentPayload.ops) || {};
      return AUGMENT_OPS.filter(o => ops[o.key]).map(o => this.$t("exportAugment.op." + o.key)).join(this.$t("exportSteps.separator"));
    },
    /** What the zip will contain */
    exportTree() {
      const root = this.exportFolderName || "…";
      const task = this.exporting.yolo_task;
      const split = this.exporting.split_on ? this.exporting.split : null;
      const subsets = split ? ["train", "val", "test"].filter(k => Number(split[k]) > 0) : ["train"];
      const { image, label } = this.exportExampleName;
      const mask = label.replace(/\.txt$/, ".png");
      const lines = task === "classify" ? ["classes.txt", `${root}/`] : ["data.yaml", "classes.txt", `${root}/`];
      const classNames = this.exportSelectedNames.slice(0, 2).map(n => this.cleanFolderName(n) || "class");
      if (this.exportSelectedNames.length > 2) classNames.push("…");
      const children = (pipe, inner) => {
        if (task === "classify") {
          classNames.forEach((name, j) => {
            const end = j === classNames.length - 1;
            lines.push(`${pipe}${end ? "└─ " : "├─ "}${name}/${name === "…" ? "" : "   " + image}`);
          });
          return;
        }
        const leaf = task === "semantic" ? ["masks/", mask] : ["labels/", label];
        if (this.exportWithImages) lines.push(`${pipe}├─ images/   ${image}`);
        lines.push(`${pipe}└─ ${leaf[0].padEnd(9)} ${leaf[1]}`);
        return inner;
      };
      if (task === "classify" && !split) {
        children("");  // class folders directly in the folder; Ultralytics splits 80/20
      } else {
        subsets.forEach((name, i) => {
          const last = i === subsets.length - 1;
          lines.push(`${last ? "└─ " : "├─ "}${name}/`);
          children(last ? "   " : "│  ");
        });
      }
      return lines.join("\n");
    },
    /** e.g. ships_IMG_0001.jpg / .txt, as the server names them */
    exportExampleName() {
      const sample = (this.main && this.main.sample) || "IMG_0001.jpg";
      const base = sample.split(/[\\/]/).pop();
      const dot = base.lastIndexOf(".");
      const stem = dot > 0 ? base.slice(0, dot) : base;
      const ext = dot > 0 ? base.slice(dot) : ".jpg";
      // merged: each file gets its own dataset name; the main one as the example
      const cleaned = String(this.mainName || "").replace(/[\\/:*?"<>|\s]+/g, "_").replace(/^[_.]+|[_.]+$/g, "");
      const name = (cleaned ? `${cleaned}_` : "") + stem;
      return { image: name + ext, label: name + ".txt" };
    },
    exportSplitSizes() {
      // the original pictures per part (augmentation comes after)
      return splitSizes(this.exportImageCount || 0, this.exporting.split);
    },
    /** originals and augmented images per part */
    exportAugCounts() {
      const sizes = this.exporting.split_on ? this.exportSplitSizes : { train: this.exportImageCount || 0, val: 0, test: 0 };
      const value = this.exporting.split_on ? this.exporting.augment : { ...this.exporting.augment, scope: "all" };
      return augmentedCounts(sizes, value);
    },
    /** originals plus their augmented versions */
    exportTotalImages() {
      if (this.exportImageCount == null) return null;
      const c = this.exportAugCounts;
      return this.exportImageCount + c.train.extra + c.val.extra + c.test.extra;
    },
    exportReady() {
      if (this.exporting.format === "yolo" && !this.exportFolderName) return false;
      if (this.exporting.augment.enabled && !this.exportAugmentPayload) return false;
      return this.exporting.categories.length > 0 && (!this.exporting.split_on || this.exportSplitValid);
    },
    /**
     * Categories offered for export: this dataset's, plus (merging) those of
     * the other datasets; the same name is one entry (ids: all of them),
     * marked when not every dataset has it.
     */
    exportCategoryList() {
      if (!this.merge.length) return this.mainCategories;
      const byName = new Map();
      const list = [];
      const add = (c, dsName) => {
        const key = String(c.name || "").trim().toLowerCase();
        let e = byName.get(key);
        if (!e) {
          e = { ...c, ids: [c.id], datasets: [] };
          byName.set(key, e);
          list.push(e);
        } else if (!e.ids.includes(c.id)) {
          e.ids.push(c.id);
        }
        if (!e.datasets.includes(dsName)) e.datasets.push(dsName);
      };
      this.mainCategories.forEach(c => add(c, this.mainName));
      this.list
        .filter(d => this.merge.includes(d.id))
        .forEach(d => d.categories.forEach(c => add(c, d.name)));
      const total = this.merge.length + 1;
      return list.map(e => (e.datasets.length < total
        ? { ...e, hint: this.$t("exportMerge.onlyIn", { names: e.datasets.join("、") }) }
        : e));
    },
    /** any category id -> the entry id standing for its name */
    exportCanon() {
      const map = {};
      this.exportCategoryList.forEach(c => (c.ids || [c.id]).forEach(id => (map[id] = c.id)));
      return map;
    },
    exportSelectedNames() {
      const byId = new Map(this.exportCategoryList.map(c => [c.id, c.name]));
      const chosen = new Set(this.exporting.categories);
      return this.exporting.order.filter(id => chosen.has(id) && byId.has(id)).map(id => byId.get(id));
    },
    /** Annotations the export will contain (pose: only those with keypoints) */
    exportAnnotationCount() {
      const counts = (this.exporting.counts && this.exporting.counts.categories) || {};
      const task = this.exporting.format === "yolo" ? this.exporting.yolo_task : null;
      return this.exporting.categories.reduce((n, id) => {
        const c = counts[id];
        if (!c) return n;
        if (task === "pose") return n + c.keypoints;
        if (task === "semantic") return n + (c.boxes || 0) + (c.rotated || 0) + (c.polygons || 0);
        return n + c.annotations;
      }, 0);
    },
    /** Images the export will contain (for the split estimate) */
    exportImageCount() {
      const counts = this.exporting.counts;
      if (!counts || counts.total_images == null) return null;
      const chosen = new Set(this.exporting.categories);
      const images = counts.image_categories || [];
      if (this.exporting.format === "yolo" && this.exporting.yolo_task === "classify") {
        // classify: images with a whole-image class, plus images whose
        // annotations are all one (ticked) category
        const classified = (counts.image_classes || []).filter(id => chosen.has(id)).length;
        const unclassified = counts.unclassified_image_categories || images;
        return classified + unclassified.filter(cats => new Set(cats.filter(id => chosen.has(id))).size === 1).length;
      }
      const matched = images.filter(cats => cats.some(id => chosen.has(id))).length;
      return this.exporting.with_empty_images ? counts.total_images - images.length + matched : matched;
    },
  },
  watch: {
    selected(now, before) {
      // a new main dataset: its task and name for the format and folder
      if (this.mainId !== this.defaultsFor) this.applyDefaults();
      if (String(now) !== String(before)) this.prepareExportCategories();
    }
  },
  methods: {
    /** Open on step 1; ``ids``: datasets ticked to start with (e.g. the dataset page's own) */
    open(ids = null) {
      if (ids) this.selected = [...ids];
      this.exporting.step = 1;
      this.loading = true;
      showModal("#exportWizard");
      return axios
        .get("/api/dataset/exportable")
        .then(r => {
          this.list = r.data.datasets || [];
          const known = this.list.map(d => d.id);
          this.selected = this.selected.filter(id => known.includes(id));
          this.applyDefaults();
          this.prepareExportCategories();
          // coming from one dataset: straight on to the format
          if (ids && ids.length && this.selected.length) this.exporting.step = 2;
        })
        .catch(() => (this.list = []))
        .finally(() => (this.loading = false));
    },
    /** format from the main dataset's planned task; the folder after its name */
    applyDefaults() {
      if (!this.main) return;
      const previous = this.list.find(d => d.id === this.defaultsFor);
      const task = this.mainTask;
      if (task && this.defaultsFor !== this.mainId) {
        this.exporting.format = "yolo";
        this.exporting.yolo_task = task;
        if (task === "classify") this.exporting.with_images = true;
      }
      const folder = this.exporting.folder.trim();
      if (!folder || (previous && folder === (this.cleanFolderName(previous.name) || "dataset"))) {
        this.exporting.folder = this.defaultExportFolder;
      }
      this.defaultsFor = this.mainId;
    },
    /** "categories differ" from the main dataset */
    mergeMismatch(d) {
      if (!this.main || d.id === this.mainId || !this.selected.includes(d.id)) return "";
      const key = c => String(c.name || "").trim().toLowerCase();
      const mine = new Set(this.mainCategories.map(key));
      const theirs = new Set(d.categories.map(key));
      const extra = d.categories.filter(c => !mine.has(key(c))).map(c => c.name);
      const missing = this.mainCategories.filter(c => !theirs.has(key(c))).map(c => c.name);
      const parts = [];
      if (extra.length) parts.push(this.$t("exportMerge.extra", { names: extra.join("、") }));
      if (missing.length) parts.push(this.$t("exportMerge.missing", { names: missing.join("、") }));
      return parts.join("；");
    },
    /** Same rules as the server (geometry/yolo_format.py safe_folder) */
    cleanFolderName(name) {
      return String(name || "").replace(/[\\/:*?"<>|\s]+/g, "_").replace(/^[_.]+|[_.]+$/g, "").slice(0, 100);
    },
    /** Step 3 (folder) only applies to YOLO */
    stepSkipped(step) {
      return step === 3 && this.exporting.format !== "yolo";
    },
    nextStep(direction) {
      let step = this.exporting.step + direction;
      while (this.stepSkipped(step)) step += direction;
      return Math.min(Math.max(step, 1), this.exportStepNames.length);
    },
    stepBy(direction) {
      this.goToStep(this.nextStep(direction));
    },
    /** A step is open once every step before it is filled in */
    canGoToStep(step) {
      if (this.stepSkipped(step)) return false;
      if (step > 1 && !this.selected.length) return false;
      if (step > 3 && this.exporting.format === "yolo" && !this.exportFolderName) return false;
      if (step > 4 && !this.exporting.categories.length) return false;
      if (step > 5 && this.exporting.split_on && !this.exportSplitValid) return false;
      if (step > 6 && this.exporting.augment.enabled && !this.exportAugmentPayload) return false;
      return true;
    },
    goToStep(step) {
      if (this.canGoToStep(step)) this.exporting.step = step;
    },
    /** Keep the order / ticks from last time; new categories go last, ticked */
    prepareExportCategories() {
      const ids = this.exportCategoryList.map(c => c.id);
      const known = new Set(this.exporting.order);
      const order = this.exporting.order.filter(id => ids.includes(id));
      const added = ids.filter(id => !known.has(id));
      this.exporting.order = [...order, ...added];
      this.exporting.categories = [
        ...this.exporting.categories.filter(id => ids.includes(id)),
        ...added
      ];
      this.exporting.counts = null;
      if (!this.mainId) return;
      const datasetIds = [this.mainId, ...this.merge];
      const seq = (this.countsSeq = (this.countsSeq || 0) + 1);
      Promise.all(datasetIds.map(id => axios.get(`/api/dataset/${id}/category_counts`).then(r => r.data)))
        .then(all => {
          if (seq === this.countsSeq) this.exporting.counts = this.mergeCounts(all);
        })
        .catch(() => (this.exporting.counts = { categories: {}, image_categories: [], total_images: null }));
    },
    /** category counts of several datasets, with same-name categories as one */
    mergeCounts(all) {
      if (all.length === 1) return all[0];
      const canon = this.exportCanon;
      const to = id => canon[id] ?? id;
      const mapList = list => [...new Set((list || []).map(to))];
      const categories = {};
      all.forEach(c => Object.entries(c.categories || {}).forEach(([id, v]) => {
        const key = String(to(Number(id)));
        const sum = categories[key] || {};
        Object.entries(v).forEach(([k, n]) => (sum[k] = (sum[k] || 0) + n));
        categories[key] = sum;
      }));
      return {
        categories,
        image_categories: all.flatMap(c => (c.image_categories || []).map(mapList)),
        image_classes: all.flatMap(c => (c.image_classes || []).map(to)),
        unclassified_image_categories: all.flatMap(c => (c.unclassified_image_categories || c.image_categories || []).map(mapList)),
        total_images: all.every(c => c.total_images != null) ? all.reduce((n, c) => n + c.total_images, 0) : null
      };
    },
    start() {
      if (!this.mainId) return;
      hideModal("#exportWizard");
      const datasetId = this.mainId;
      const names = this.exportDatasetNames;
      const options = { format: this.exporting.format };
      if (this.exporting.only_approved) options.only_approved = true;
      options.with_images = this.exportWithImages;
      if (this.exporting.format === "yolo") {
        options.yolo_task = this.exporting.yolo_task;
        options.folder = this.exportFolderName;
      }
      if (this.exportAugmentPayload) options.augment = JSON.stringify(this.exportAugmentPayload);
      if (this.exporting.split_on) {
        const r = this.exporting.split;
        options.split = [r.train, r.val, r.test].map(v => Number(v) || 0).join(",");
        options.seed = this.exporting.seed;
      }
      // ticked categories in the chosen order (= YOLO class index)
      const chosen = new Set(this.exporting.categories);
      let categories = this.exporting.order.filter(id => chosen.has(id));
      if (this.merge.length) {
        // every dataset's category of that name (the server keeps one per name)
        const byId = new Map(this.exportCategoryList.map(c => [c.id, c.ids || [c.id]]));
        categories = categories.flatMap(id => byId.get(id) || [id]);
        options.with_datasets = this.merge.join(",");
      }
      Dataset.exportingCOCO(this.mainId, categories, this.exporting.with_empty_images, options)
        .then(response => {
          this.$emit("started", { datasetId, taskId: response.data.id, names });
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.$toastr.error(data.message || String(error), this.$t("dataset.exportFailed"));
        });
    },
  }
};
</script>

<style scoped>
/* seven steps: a little wider, labels on one line */
.wizard-dialog {
  max-width: 600px;
}
.export-steps .step-name {
  white-space: nowrap;
}
.pick-list {
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 4px 8px;
}
.pick-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 2px;
  margin: 0;
  cursor: pointer;
}
.export-steps {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  counter-reset: step;
}
.export-steps li {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  position: relative;
  cursor: pointer;
  color: #6c757d;
  font-size: 0.85rem;
}
.export-steps li.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.export-steps li:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 15px;
  left: calc(50% + 20px);
  right: calc(-50% + 20px);
  height: 2px;
  background: #dee2e6;
}
.export-steps li.done:not(:last-child)::after {
  background: #198754;
}
.export-steps .step-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid #ced4da;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}
.export-steps li.active {
  color: #0d6efd;
  font-weight: 600;
}
.export-steps li.active .step-dot {
  border-color: #0d6efd;
  background: #0d6efd;
  color: #fff;
}
.export-steps li.done .step-dot {
  border-color: #198754;
  background: #198754;
  color: #fff;
}
.choice-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  height: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  cursor: pointer;
  margin: 0;
}
.choice-card:hover {
  border-color: #86b7fe;
}
.choice-card.selected {
  border-color: #0d6efd;
  box-shadow: 0 0 0 1px #0d6efd;
  background: rgba(13, 110, 253, 0.05);
}
.export-summary {
  background: #f8f9fa;
  border-radius: 0.5rem;
  padding: 0.6rem 0.75rem;
}
.zip-tree {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  white-space: pre;
  overflow-x: auto;
}
.export-steps li.skipped .step-dot {
  border-style: dashed;
  color: #adb5bd;
}
.export-steps li.skipped {
  opacity: 0.5;
}
</style>
