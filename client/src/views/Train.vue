<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="bg-light train-page" style="overflow: auto; height: calc(var(--vh) - 55px)">
      <div class="page-container py-4">
        <div class="d-flex align-items-start flex-wrap gap-2 mb-3">
          <div class="me-auto">
            <h3 class="mb-1"><i class="fa fa-graduation-cap" /> {{ $t('train.title') }}</h3>
            <div class="text-muted small">{{ $t('train.subtitle') }}</div>
          </div>
          <div v-if="status" class="d-flex flex-wrap gap-2 align-items-center justify-content-end">
            <span
              v-for="tr in status.trainers || []"
              :key="tr.name"
              class="trainer-pill"
              :class="tr.alive ? (tr.run_id ? 'busy' : tr.gpu && tr.gpu.busy ? 'other' : 'ok') : 'down'"
              :title="trainerTitle(tr)"
            >
              <i class="fa me-1" :class="tr.kind === 'remote' ? 'fa-server' : 'fa-desktop'" />
              <b>{{ tr.name }}</b>
              <span v-if="tr.device" class="fw-normal"> · {{ tr.device }}</span>
              <span class="fw-normal"> · {{ trainerState(tr) }}</span>
              <span v-if="tr.alive && tr.gpu && tr.gpu.mem_total" class="fw-normal gpu-use">
                · {{ gpuUse(tr.gpu) }}
              </span>
            </span>
            <span v-if="!(status.trainers || []).length" class="trainer-pill down">
              <i class="fa fa-exclamation-circle" /> {{ $t('train.down') }}
            </span>
            <button v-if="status.can_manage" type="button" class="btn btn-sm btn-outline-secondary" @click="toggleServers">
              <i class="fa fa-server" /> {{ $t('train.servers.manage') }}
            </button>
          </div>
        </div>

        <!-- other servers that train (admins) -->
        <div v-if="showServers" class="card p-3 shadow-sm mb-3">
          <h6 class="border-bottom pb-2 d-flex align-items-center">
            <b class="me-auto"><i class="fa fa-server" /> {{ $t('train.servers.title') }}</b>
            <button type="button" class="btn-close" :aria-label="$t('train.servers.close')" @click="showServers = false" />
          </h6>
          <div class="small text-muted mb-2">{{ $t('train.servers.intro') }}</div>
          <table v-if="servers.length" class="table table-sm align-middle small mb-2">
            <thead>
              <tr>
                <th>{{ $t('train.servers.name') }}</th>
                <th>{{ $t('train.servers.state') }}</th>
                <th>{{ $t('train.servers.ip') }}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="w in servers" :key="w.name">
                <td><b>{{ w.name }}</b></td>
                <td>
                  <template v-if="trainerOf(w.name) && trainerOf(w.name).alive">
                    <i class="fa fa-circle text-success" /> {{ trainerOf(w.name).device }}
                  </template>
                  <span v-else class="text-muted"><i class="fa fa-circle-o" /> {{ $t('train.servers.offline') }}</span>
                </td>
                <td class="text-muted">{{ w.last_ip || '—' }}</td>
                <td class="text-end text-nowrap">
                  <button type="button" class="btn btn-sm btn-link" @click="newToken(w)">{{ $t('train.servers.newToken') }}</button>
                  <button type="button" class="btn btn-sm btn-link text-danger" @click="removeServer(w)"><i class="fa fa-trash" /></button>
                </td>
              </tr>
            </tbody>
          </table>
          <form class="d-flex flex-wrap gap-2 align-items-center" @submit.prevent="addServer">
            <input v-model.trim="newServer" class="form-control form-control-sm server-name" :placeholder="$t('train.servers.namePlaceholder')" maxlength="40" />
            <button type="submit" class="btn btn-sm btn-primary" :disabled="!newServer"><i class="fa fa-plus" /> {{ $t('train.servers.add') }}</button>
          </form>
          <div v-if="setup" class="setup mt-3">
            <div class="fw-semibold small mb-1">{{ $t('train.servers.setupTitle', { name: setup.name }) }}</div>
            <div class="small text-warning-emphasis mb-1"><i class="fa fa-key" /> {{ $t('train.servers.tokenOnce') }}</div>
            <pre class="command">{{ setupScript }}</pre>
            <div class="d-flex gap-2 align-items-center">
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="copySetup"><i class="fa fa-copy" /> {{ $t('train.servers.copy') }}</button>
              <span class="small text-muted">{{ $t('train.servers.setupHint') }}</span>
            </div>
          </div>
        </div>
        <div v-if="status && !status.alive" class="alert alert-warning small">{{ $t('train.downHint') }}</div>

        <!-- a new training -->
        <div ref="newForm" class="card p-3 shadow-sm mb-3">
          <h6 class="border-bottom pb-2"><b>{{ $t('train.new') }}</b></h6>
          <div v-if="!exports.length && !loading" class="text-muted small">{{ $t('train.noExports') }}</div>
          <div v-else class="row g-3">
            <div class="col-lg-6">
              <label class="form-label fw-semibold mb-1" for="trainExport">{{ $t('train.export') }}</label>
              <select id="trainExport" v-model="form.export_id" class="form-select form-select-sm">
                <option v-for="e in exports" :key="e.id" :value="e.id">{{ exportLabel(e) }}</option>
              </select>
              <div v-if="chosenExport" class="small text-muted mt-1">
                {{ $t('train.task') }}：<b>{{ $t('yolo.' + chosenExport.task) }}</b>
                · {{ $t('train.classes', { names: chosenExport.categories.join('、') || '—' }) }}
                <template v-if="chosenExport.split_counts">
                  · {{ $t('train.splitCounts', chosenExport.split_counts) }}
                </template>
              </div>
              <div v-if="chosenExport && !chosenExport.split" class="small text-warning-emphasis mt-1">
                <i class="fa fa-exclamation-triangle" /> {{ $t('train.noSplit') }}
              </div>

              <div class="fw-semibold mt-3 mb-1">{{ $t('train.start') }}</div>
              <div class="btn-group btn-group-sm mb-2 flex-wrap" role="group">
                <button
                  v-for="src in ['catalog', 'models', 'upload']"
                  :key="src"
                  type="button"
                  class="btn"
                  :class="form.source === src ? 'btn-primary' : 'btn-outline-primary'"
                  :disabled="src === 'models' && !models.length"
                  @click="form.source = src"
                >
                  {{ $t({ catalog: 'train.fromBase', models: 'train.fromModel', upload: 'train.fromUpload' }[src]) }}
                </button>
              </div>

              <!-- official models: .pt pretrained or .yaml from scratch -->
              <template v-if="form.source === 'catalog'">
                <div class="d-flex flex-wrap gap-2 align-items-center">
                  <select v-model="form.family" class="form-select form-select-sm w-auto" :aria-label="$t('train.family')">
                    <option v-for="f in families" :key="f.key" :value="f.key">{{ f.label }}</option>
                  </select>
                  <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn" :class="form.kind === 'pt' ? 'btn-secondary' : 'btn-outline-secondary'" @click="form.kind = 'pt'">
                      {{ $t('train.kindPt') }}
                    </button>
                    <button type="button" class="btn" :class="form.kind === 'yaml' ? 'btn-secondary' : 'btn-outline-secondary'" @click="form.kind = 'yaml'">
                      {{ $t('train.kindYaml') }}
                    </button>
                  </div>
                </div>
                <div v-if="!variants.length" class="small text-warning-emphasis mt-2">
                  {{ $t('train.noModelsForTask', { task: chosenExport ? $t('yolo.' + chosenExport.task) : '' }) }}
                </div>
                <div v-else class="variants mt-2">
                  <button
                    v-for="v in variants"
                    :key="v.name"
                    type="button"
                    class="btn btn-sm"
                    :class="form.model === v.name ? 'btn-dark' : 'btn-outline-secondary'"
                    :title="v.scale && $te('train.size.' + v.scale) ? $t('train.size.' + v.scale) : v.name"
                    @click="form.model = v.name"
                  >{{ v.name }}</button>
                </div>
                <div v-if="chosenVariant && chosenVariant.scale && $te('train.size.' + chosenVariant.scale)" class="small mt-1">
                  <code>{{ chosenVariant.name }}</code> · {{ $t('train.size.' + chosenVariant.scale) }}
                </div>
                <div class="small text-muted mt-1">{{ form.kind === 'pt' ? $t('train.kindPtHint') : $t('train.kindYamlHint') }}</div>
              </template>

              <template v-else-if="form.source === 'models'">
                <select v-model="form.base_model" class="form-select form-select-sm">
                  <option v-for="m in models" :key="m.name" :value="m.name">{{ m.name }}<template v-if="m.task"> ({{ m.task }})</template></option>
                </select>
                <div class="small text-muted mt-1">{{ $t('train.fromModelHint') }}</div>
              </template>

              <template v-else>
                <div v-if="!uploads.length" class="small text-muted">{{ $t('train.uploadsNone') }}</div>
                <div v-else class="uploads">
                  <label v-for="u in uploads" :key="u.id" class="upload-row" :class="{ on: form.upload_id === u.id }">
                    <input v-model="form.upload_id" class="form-check-input mt-0" type="radio" :value="u.id" />
                    <span class="badge" :class="u.kind === 'pt' ? 'text-bg-info' : 'text-bg-light border'">.{{ u.kind }}</span>
                    <span class="text-truncate flex-grow-1">{{ u.name }}</span>
                    <span class="small text-muted text-nowrap">{{ fmtSize(u.size) }} · {{ $t('train.uploadedBy', { user: u.uploader }) }}</span>
                    <button type="button" class="btn btn-sm btn-link text-danger p-0" :title="$t('train.remove')" @click.prevent="removeUpload(u)">
                      <i class="fa fa-trash" />
                    </button>
                  </label>
                </div>
                <div class="d-flex align-items-center gap-2 mt-2">
                  <button type="button" class="btn btn-sm btn-outline-primary" :disabled="uploadPct != null" @click="$refs.modelFile.click()">
                    <i class="fa" :class="uploadPct != null ? 'fa-spinner fa-spin' : 'fa-upload'" />
                    {{ uploadPct != null ? $t('train.uploading', { pct: uploadPct }) : $t('train.uploadModel') }}
                  </button>
                  <input ref="modelFile" type="file" accept=".pt,.yaml,.yml" class="d-none" @change="uploadModel" />
                </div>
                <div class="small text-muted mt-1">{{ $t('train.uploadHint') }}</div>
              </template>

              <!-- weights for an architecture -->
              <div v-if="isYamlModel" class="mt-2">
                <label class="form-label small mb-0" for="trainWeights">{{ $t('train.loadWeights') }}</label>
                <select id="trainWeights" v-model="form.pretrained" class="form-select form-select-sm">
                  <option value="">{{ $t('train.noWeights') }}</option>
                  <option v-for="w in weightChoices" :key="w.value" :value="w.value">{{ w.label }}</option>
                </select>
              </div>
            </div>

            <div class="col-lg-6">
              <div class="row g-2">
                <div class="col-6">
                  <label class="form-label small mb-0" for="trainEpochs">{{ $t('train.epochs') }}</label>
                  <input id="trainEpochs" v-model.number="form.epochs" type="number" min="1" max="1000" class="form-control form-control-sm" />
                </div>
                <div class="col-6">
                  <label class="form-label small mb-0" for="trainImgsz">{{ $t('train.imgsz') }}</label>
                  <input id="trainImgsz" v-model.number="form.imgsz" type="number" min="32" max="2048" step="32" list="trainImgszList" class="form-control form-control-sm" />
                  <datalist id="trainImgszList">
                    <option v-for="v in [320, 416, 512, 640, 768, 960, 1024, 1280]" :key="v" :value="v" />
                  </datalist>
                </div>
                <div class="col-6">
                  <label class="form-label small mb-0" for="trainBatch">{{ $t('train.batch') }}</label>
                  <input id="trainBatch" v-model.number="form.batch" type="number" min="-1" max="512" step="any" list="trainBatchList" class="form-control form-control-sm" :title="$t('train.batchAuto')" />
                  <datalist id="trainBatchList">
                    <option value="-1">{{ $t('train.batchAuto') }}</option>
                    <option v-for="v in [4, 8, 16, 32, 64]" :key="v" :value="v" />
                  </datalist>
                </div>
                <div class="col-6">
                  <label class="form-label small mb-0" for="trainPatience">{{ $t('train.patience') }}</label>
                  <input id="trainPatience" v-model.number="form.patience" type="number" min="0" max="1000" class="form-control form-control-sm" />
                </div>
                <div class="col-12">
                  <label class="form-label small mb-0" for="trainName">{{ $t('train.name') }}</label>
                  <input id="trainName" v-model="form.name" class="form-control form-control-sm" :placeholder="chosenExport ? chosenExport.datasets.join(' + ') : ''" />
                </div>
                <div v-if="status && (status.trainers || []).length > 1" class="col-12">
                  <label class="form-label small mb-0" for="trainTarget">{{ $t('train.servers.where') }}</label>
                  <select id="trainTarget" v-model="form.target" class="form-select form-select-sm">
                    <option value="">{{ $t('train.servers.any') }}</option>
                    <option v-for="tr in status.trainers" :key="tr.name" :value="tr.name">
                      {{ tr.name }}{{ tr.device ? ' · ' + tr.device : '' }} · {{ trainerState(tr) }}
                    </option>
                  </select>
                </div>
              </div>
              <div class="small text-muted mt-2">{{ $t('train.paramsHint') }}</div>
              <div class="d-flex align-items-center gap-2 mt-3">
                <button type="button" class="btn btn-primary" :disabled="!form.export_id || busy" @click="start">
                  <i class="fa" :class="busy ? 'fa-spinner fa-spin' : 'fa-play'" /> {{ $t('train.go') }}
                </button>
                <span v-if="status && (status.running || status.queued)" class="small text-muted">
                  {{ $t('train.queueNow', { running: status.running, queued: status.queued }) }}
                </span>
              </div>
            </div>
          </div>

          <!-- augmentation: in the export, and while training -->
          <div v-if="chosenExport" class="mt-3 border-top pt-2">
            <div class="fw-semibold mb-1"><i class="fa fa-magic" /> {{ $t('trainAug.title') }}</div>
            <TrainAugment
              :export-augment="chosenExport.augment"
              :defaults="catalog.args"
              :extra="typedArgs"
              :task="task"
              editable
              @edit="editArg"
            />
            <div class="small text-muted">{{ $t('trainAug.editHint') }}</div>
          </div>

          <!-- any other Ultralytics argument -->
          <div v-if="exports.length" class="mt-3 border-top pt-2">
            <button type="button" class="btn btn-sm btn-link px-0 text-decoration-none fw-semibold" @click="showAdvanced = !showAdvanced">
              <i class="fa" :class="showAdvanced ? 'fa-caret-down' : 'fa-caret-right'" />
              {{ $t('train.advanced') }}
              <span v-if="Object.keys(typedArgs).length" class="badge text-bg-primary ms-1">{{ Object.keys(typedArgs).length }}</span>
            </button>
            <div v-show="showAdvanced">
              <div class="small text-muted mb-2">
                {{ $t('train.advancedHint') }}
                <a href="https://docs.ultralytics.com/modes/train/#train-settings" target="_blank" rel="noopener">{{ $t('train.argsDocs') }} <i class="fa fa-external-link" /></a>
              </div>
              <TrainArgsTable ref="argsTable" v-model="form.overrides" :defaults="catalog.args || {}" :exclude="TABLE_EXCLUDE" />
              <div class="d-flex flex-wrap gap-2 mt-2">
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="$refs.argsFile.click()">
                  <i class="fa fa-file-text-o" /> {{ $t('train.loadArgs') }}
                </button>
                <input ref="argsFile" type="file" accept=".yaml,.yml" class="d-none" @change="loadArgsFile" />
              </div>
              <div v-if="argsNote" class="small text-muted mt-1">{{ argsNote }}</div>
            </div>
            <div class="small text-muted mt-2">{{ $t('train.command') }}</div>
            <pre class="command">{{ commandPreview }}</pre>
          </div>
        </div>

        <!-- runs -->
        <div class="card p-3 shadow-sm">
          <h6 class="border-bottom pb-2 d-flex align-items-center">
            <b class="me-auto">{{ $t('train.runs') }}</b>
            <button type="button" class="btn btn-sm btn-outline-secondary py-0" @click="loadRuns"><i class="fa fa-refresh" /></button>
          </h6>
          <div v-if="!runs.length" class="text-muted small">{{ $t('train.noRuns') }}</div>
          <div v-for="r in runs" :key="r.id" class="run" :class="{ open: openId === r.id }">
            <div class="run-head" role="button" @click="toggle(r)">
              <span class="badge" :class="statusClass(r.status)">{{ $t('train.status.' + r.status) }}</span>
              <span class="fw-semibold text-truncate run-name">#{{ r.id }} {{ r.name }}</span>
              <span class="small text-muted text-nowrap run-model" :title="modelLabel(r)">
                {{ $t('yolo.' + r.task) }} · {{ modelLabel(r) }}<template v-if="whereLabel(r)"> · <i class="fa fa-server" /> {{ whereLabel(r) }}</template>
              </span>
              <span class="run-progress">
                <span class="progress" style="height: 8px">
                  <span class="progress-bar" :class="r.status === 'failed' ? 'bg-danger' : 'bg-success'" :style="{ width: pct(r) + '%' }" />
                </span>
                <span class="small text-muted text-nowrap">
                  <template v-if="r.status === 'queued'">{{ $t('train.queuePos', { n: r.queue_position }) }}</template>
                  <template v-else>{{ r.epoch }} / {{ r.epochs }}</template>
                </span>
              </span>
              <span v-if="r.best" class="small text-nowrap metric" :title="$t('train.best.title', { epoch: r.best.epoch })">
                <i class="fa fa-star text-warning" /> {{ mainMetric(r.best.metrics) }} <span class="text-muted">@{{ r.best.epoch }}</span>
              </span>
              <span v-else class="small text-nowrap metric" :title="mainMetricKey(r.last) || ''">{{ mainMetric(r.last) }}</span>
              <span class="small text-muted text-nowrap d-none d-md-inline creator">{{ r.creator }}</span>
              <i class="fa" :class="openId === r.id ? 'fa-chevron-up' : 'fa-chevron-down'" />
            </div>

            <div v-if="openId === r.id && detail" class="run-body">
              <div class="d-flex flex-wrap gap-2 align-items-center mb-2 small">
                <span>{{ $t('train.fromExport', { id: r.export_id, names: r.dataset_names.join(' + ') }) }}</span>
                <span class="text-muted">· epochs {{ r.params.epochs }} · imgsz {{ r.params.imgsz }} · batch {{ r.params.batch === -1 ? $t('train.batchAuto') : r.params.batch }} · patience {{ r.params.patience }}</span>
                <span v-if="r.params.extra && Object.keys(r.params.extra).length" class="text-muted text-break">
                  · {{ $t('train.extra') }}：<code>{{ extraText(r.params.extra) }}</code>
                </span>
                <span class="ms-auto d-flex gap-2">
                  <button
                    v-if="r.status === 'running' || r.status === 'queued'"
                    type="button"
                    class="btn btn-sm btn-outline-danger"
                    :disabled="r.stop_requested"
                    @click="stop(r)"
                  >
                    <i class="fa fa-stop" />
                    {{ r.status === 'queued' ? $t('train.cancel') : r.stop_requested ? $t('train.stopping') : $t('train.stop') }}
                  </button>
                  <button
                    v-if="r.status !== 'queued'"
                    type="button"
                    class="btn btn-sm btn-outline-primary"
                    :title="$t('train.reuseHint')"
                    @click="reuse(detail)"
                  >
                    <i class="fa fa-clone" /> {{ $t('train.reuse') }}
                  </button>
                  <button
                    v-if="detail.resumable && (r.creator === ($store.state.user.user || {}).username || $store.getters['user/isAdmin'])"
                    type="button"
                    class="btn btn-sm btn-primary"
                    :title="$t('train.resumeHint')"
                    @click="resume(r)"
                  >
                    <i class="fa fa-play" /> {{ $t('train.resume', { n: r.epoch }) }}
                  </button>
                  <a
                    v-if="detail.archive"
                    class="btn btn-sm btn-success"
                    :href="`/api/train/${r.id}/download`"
                    download
                    :title="$t('train.downloadHint')"
                  >
                    <i class="fa fa-download" /> {{ $t('train.download') }}
                    <span v-if="detail.archive.size" class="opacity-75">（{{ fmtSize(detail.archive.size) }}）</span>
                  </a>
                  <button v-if="r.status !== 'running' && r.status !== 'queued'" type="button" class="btn btn-sm btn-outline-secondary" @click="remove(r)">
                    <i class="fa fa-trash" /> {{ $t('train.remove') }}
                  </button>
                </span>
              </div>

              <div v-if="detail.model_name" class="alert alert-success py-2 small mb-2">
                <i class="fa fa-check" /> {{ $t('train.saved') }} <code>{{ detail.model_name }}</code>
                <RouterLink class="ms-2" to="/models">{{ $t('train.toModels') }}</RouterLink>
              </div>
              <div v-if="detail.error" class="alert alert-danger py-2 small mb-2 text-break">{{ detail.error }}</div>
              <div v-if="detail.params.resumes" class="small text-muted mb-2">
                <i class="fa fa-history" /> {{ $t('train.resumed', { n: detail.params.resumes }) }}
              </div>

              <div class="aug-detail mb-2">
                <div class="fw-semibold small mb-1"><i class="fa fa-magic" /> {{ $t('trainAug.title') }}</div>
                <TrainAugment
                  :export-augment="detail.params.export_augment"
                  :defaults="catalog.args"
                  :extra="detail.params.extra || {}"
                  :task="r.task"
                />
              </div>

              <div v-if="detail.best" class="best-bar mb-2">
                <span class="fw-semibold"><i class="fa fa-star text-warning" /> {{ $t('train.best.label', { epoch: detail.best.epoch }) }}</span>
                <span v-for="m in bestMetrics" :key="m.key" class="best-metric">{{ m.name }} <b>{{ m.value }}</b></span>
                <span class="text-muted">
                  <template v-if="detail.status === 'running'">
                    {{ detail.best.since ? $t('train.best.since', { n: detail.best.since, patience: detail.params.patience }) : $t('train.best.latest') }}
                  </template>
                  <template v-else-if="detail.model_name">{{ $t('train.best.saved') }}</template>
                </span>
                <span class="text-muted small ms-auto" :title="$t('train.best.howHint')">{{ $t('train.best.how', { rule: fitnessRule }) }}</span>
              </div>

              <template v-if="chartGroups.length">
                <div class="d-flex align-items-center gap-2 small mb-1 flex-wrap">
                  <span class="fw-semibold"><i class="fa fa-line-chart" /> {{ $t('train.curves') }}</span>
                  <span v-if="steps.points.length" class="text-muted">{{ $t('train.stepsCount', { n: steps.total }) }}</span>
                  <label class="ms-auto d-flex align-items-center gap-2 mb-0" for="trainSmoothing">
                    {{ $t('train.smoothing') }}
                    <input id="trainSmoothing" v-model.number="smoothing" type="range" min="0" max="0.99" step="0.01" class="form-range smoothing" />
                    <span class="text-muted smoothing-value">{{ smoothing.toFixed(2) }}</span>
                  </label>
                </div>
                <div v-for="g in chartGroups" :key="g.key" class="mb-2">
                  <div class="small text-muted mb-1">{{ g.title }}</div>
                  <div class="row g-2">
                    <div v-for="c in g.charts" :key="c.key" class="col-xl-4 col-md-6">
                      <ScalarChart
                        :title="c.title"
                        :hint="c.hint"
                        :series="c.series"
                        :smoothing="smoothing"
                        :marker="detail.best ? detail.best.epoch : null"
                        :marker-label="$t('train.best.short')"
                      />
                    </div>
                  </div>
                </div>
              </template>
              <div class="fw-semibold small mt-2 mb-1">{{ $t('train.log') }}</div>
              <pre ref="log" class="train-log">{{ logText || '…' }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import ScalarChart from "@/components/ScalarChart.vue";
import TrainAugment from "@/components/TrainAugment.vue";
import TrainArgsTable from "@/components/TrainArgsTable.vue";
import { parseArgValue, showValue } from "@/libs/trainArgs";
import { REPO_URL } from "@/links";

const POLL_MS = 3000;
// the output of the training that is open, while it runs
const LIVE_MS = 1000;
const MAIN_ARGS = ["epochs", "imgsz", "batch", "patience"];

const SMOOTHING_KEY = "train.smoothing";
const COLORS = { batch: "#2a78d6", train: "#2a78d6", val: "#e8590c" };
const PG_COLORS = ["#1a9e6e", "#8a5cd1", "#d6336c"];
const METRIC_ORDER = ["precision", "recall", "mAP50", "mAP50-95", "accuracy_top1", "accuracy_top5"];
const MAX_STEPS = 8000;

function readSmoothing() {
  try {
    const v = parseFloat(localStorage.getItem(SMOOTHING_KEY));
    return Number.isFinite(v) ? Math.min(0.99, Math.max(0, v)) : 0.6;
  } catch {
    return 0.6;
  }
}

/** keep a long list of points light: every other one (each epoch's end stays) */
function thin(points) {
  return points.filter((p, i) => i % 2 === 0 || i === points.length - 1 || Number.isInteger(p.x));
}

/** Training YOLO models on the server (the trainer service runs them one at a time). */
export default {
  name: "TrainPage",
  components: { ScalarChart, TrainAugment, TrainArgsTable },
  data() {
    return {
      status: null,
      catalog: { families: [], args: {}, blocked: [] },
      exports: [],
      models: [],
      uploads: [],
      runs: [],
      loading: true,
      busy: false,
      openId: null,
      detail: null,
      timer: null,
      showAdvanced: false,
      // other servers that train (admins)
      showServers: false,
      servers: [],
      newServer: "",
      setup: null,
      // the open run's output, pushed as it is written: {runId, lines, progress}
      live: null,
      // points within the epochs (progress bar) of the open run
      steps: { runId: null, points: [], total: 0 },
      smoothing: readSmoothing(),
      argsNote: "",
      uploadPct: null,
      form: {
        export_id: null,
        source: "catalog",
        family: "yolo26",
        kind: "pt",
        model: "",
        base_model: "",
        upload_id: null,
        pretrained: "",
        epochs: 100,
        imgsz: 640,
        batch: -1,
        patience: 50,
        name: "",
        // the trainer (server) to train on; empty: whichever is free
        target: "",
        // training arguments changed from their defaults: {name: text}
        overrides: {}
      },
      // the main ones have their own fields; pretrained is the weights choice
      TABLE_EXCLUDE: [...MAIN_ARGS, "pretrained"]
    };
  },
  computed: {
    chosenExport() {
      return this.exports.find(e => e.id === this.form.export_id) || null;
    },
    task() {
      return (this.chosenExport || {}).task || "detect";
    },
    /** families with a model for the export's task */
    families() {
      return (this.catalog.families || []).filter(f => f.items.some(i => i.task === this.task));
    },
    variants() {
      const fam = this.families.find(f => f.key === this.form.family);
      if (!fam) return [];
      const order = s => {
        const i = ["n", "t", "s", "m", "b", "l", "x"].indexOf(s);
        return i < 0 ? 9 : i;
      };
      // n s m l x, the plain one before its variants (-p2, -ghost…)
      return fam.items
        .filter(i => i.task === this.task && i.kind === this.form.kind)
        .sort((a, b) => order(a.scale) - order(b.scale) || a.name.length - b.name.length || a.name.localeCompare(b.name));
    },
    chosenVariant() {
      return this.variants.find(v => v.name === this.form.model) || null;
    },
    chosenUpload() {
      return this.uploads.find(u => u.id === this.form.upload_id) || null;
    },
    /** the model to train, as on the command line */
    modelName() {
      if (this.form.source === "models") return this.form.base_model;
      if (this.form.source === "upload") return this.chosenUpload ? this.chosenUpload.name : "";
      return this.chosenVariant ? this.chosenVariant.name : "";
    },
    isYamlModel() {
      if (this.form.source === "catalog") return this.form.kind === "yaml";
      return this.form.source === "upload" && !!this.chosenUpload && this.chosenUpload.kind === "yaml";
    },
    /** weights to load into an architecture: the same family first */
    weightChoices() {
      const out = [];
      const fams = [...this.families].sort((a, b) => (b.key === this.form.family) - (a.key === this.form.family));
      fams.forEach(f =>
        f.items.filter(i => i.kind === "pt" && i.task === this.task).forEach(i => out.push({ value: i.name, label: i.name }))
      );
      this.uploads.filter(u => u.kind === "pt").forEach(u => out.push({ value: `upload:${u.id}`, label: `${u.name} (${this.$t("train.fromUpload")})` }));
      return out;
    },
    /** charts like TensorBoard: metrics, losses (within each epoch too),
     *  learning rate, GPU memory */
    chartGroups() {
      if (!this.detail) return [];
      const rows = this.detail.metrics || [];
      const keys = [...new Set(rows.flatMap(r => Object.keys(r)))];
      const steps = this.steps.runId === this.openId ? this.steps.points : [];
      const byEpoch = key => rows.filter(r => r[key] != null).map((r, i) => [r.epoch != null ? r.epoch : i + 1, r[key]]);
      const suffix = { B: this.$t("train.curve.box"), M: this.$t("train.curve.mask"), P: this.$t("train.curve.pose") };
      const groups = [];

      const metrics = keys
        .filter(k => k.startsWith("metrics/"))
        .map(k => {
          const m = k.match(/^metrics\/(.*?)(?:\((\w)\))?$/);
          return { key: k, name: m[1], kind: m[2] };
        })
        .sort((a, b) => (a.kind || "").localeCompare(b.kind || "") || (METRIC_ORDER.indexOf(a.name) + 1 || 99) - (METRIC_ORDER.indexOf(b.name) + 1 || 99));
      if (metrics.length) {
        groups.push({
          key: "metrics",
          title: this.$t("train.curve.metrics"),
          charts: metrics.map(m => ({
            key: m.key,
            title: m.name,
            hint: [m.kind && suffix[m.kind], this.$te("train.curve.hint." + m.name) ? this.$t("train.curve.hint." + m.name) : ""].filter(Boolean).join(" · "),
            series: [{ name: this.$t("train.curve.val"), color: COLORS.val, points: byEpoch(m.key), dots: true }]
          }))
        });
      }

      const losses = keys.filter(k => k.startsWith("train/")).map(k => k.slice(6));
      if (losses.length) {
        groups.push({
          key: "losses",
          title: this.$t("train.curve.losses"),
          charts: losses.map(name => {
            const series = [];
            const batch = steps.filter(p => p[name] != null).map(p => [p.x, p[name]]);
            if (batch.length) series.push({ name: this.$t("train.curve.batch"), color: COLORS.batch, points: batch });
            else series.push({ name: this.$t("train.curve.train"), color: COLORS.train, points: byEpoch("train/" + name), dots: true });
            if (keys.includes("val/" + name)) {
              series.push({ name: this.$t("train.curve.val"), color: COLORS.val, points: byEpoch("val/" + name), dots: true });
            }
            return { key: name, title: name, hint: this.$te("train.curve.hint." + name) ? this.$t("train.curve.hint." + name) : "", series };
          })
        });
      }

      const other = [];
      const lrs = keys.filter(k => k.startsWith("lr/")).sort();
      if (lrs.length) {
        other.push({
          key: "lr",
          title: "lr",
          hint: this.$t("train.curve.hint.lr"),
          series: lrs.map((k, i) => ({ name: k.slice(3), color: PG_COLORS[i % PG_COLORS.length], points: byEpoch(k) }))
        });
      }
      const mem = steps.filter(p => p.gpu_mem != null).map(p => [p.x, p.gpu_mem]);
      if (mem.some(p => p[1] > 0)) {
        other.push({ key: "gpu", title: "gpu_mem", hint: this.$t("train.curve.hint.gpu_mem"), series: [{ name: "GB", color: "#495057", points: mem }] });
      }
      const times = byEpoch("time");
      if (times.length > 1) {
        const perEpoch = times.map((p, i) => [p[0], i ? p[1] - times[i - 1][1] : p[1]]);
        other.push({ key: "time", title: "time", hint: this.$t("train.curve.hint.time"), series: [{ name: "s", color: "#a07c00", points: perEpoch, dots: true }] });
      }
      if (other.length) groups.push({ key: "other", title: this.$t("train.curve.other"), charts: other });
      return groups;
    },
    bestMetrics() {
      const m = (this.detail && this.detail.best && this.detail.best.metrics) || {};
      const kinds = { B: this.$t("train.curve.box"), M: this.$t("train.curve.mask"), P: this.$t("train.curve.pose") };
      const many = new Set(Object.keys(m).map(k => (k.match(/\((\w)\)$/) || [])[1])).size > 1;
      return Object.keys(m)
        .filter(k => /(mAP50|mAP50-95|precision|recall|accuracy_top1|accuracy_top5|mIoU)(\(\w\))?$/.test(k))
        .map(k => {
          const [, name, kind] = k.match(/^metrics\/(.*?)(?:\((\w)\))?$/);
          return { key: k, name: many && kind ? `${name}（${kinds[kind] || kind}）` : name, value: m[k].toFixed(3) };
        });
    },
    /** how Ultralytics picks best.pt, in words */
    fitnessRule() {
      const w = (this.detail && this.detail.fitness_weights) || this.catalog.fitness || [0, 0, 0.1, 0.9];
      const names = ["P", "R", "mAP50", "mAP50-95"];
      const parts = w.map((v, i) => (v ? (v === 1 ? names[i] : `${v}×${names[i]}`) : null)).filter(Boolean);
      if (this.detail && this.detail.task === "classify") return "(top-1 + top-5) / 2";
      return parts.join(" + ");
    },
    setupScript() {
      if (!this.setup) return "";
      return [
        `# ${this.$t("train.servers.onOther", { name: this.setup.name })}`,
        `git clone -b upgrade-2026 ${REPO_URL}.git coco-annotator`,
        "cd coco-annotator",
        "cat > .env <<'EOF'",
        `TRAINER_URL=${window.location.origin}`,
        `TRAINER_TOKEN=${this.setup.token}`,
        "EOF",
        "sudo docker compose -f docker-compose.worker.yml up -d"
      ].join("\n");
    },
    logText() {
      if (this.live && this.live.runId === this.openId) {
        const lines = this.live.progress ? [...this.live.lines, this.live.progress] : this.live.lines;
        return lines.join("\n");
      }
      return this.detail ? this.detail.log_tail : "";
    },
    /** own arguments with their values as they will be sent */
    typedArgs() {
      const out = {};
      Object.entries(this.form.overrides).forEach(([k, v]) => {
        if (String(v).trim() !== "") out[k] = parseArgValue(v);
      });
      return out;
    },
    commandPreview() {
      const f = this.form;
      const parts = [`yolo ${this.task} train`, `model=${this.modelName || "?"}`, `data=<${this.chosenExport ? this.$t("train.fromExport", { id: f.export_id, names: this.chosenExport.datasets.join(" + ") }) : "?"}>`];
      parts.push(`epochs=${f.epochs}`, `imgsz=${f.imgsz}`, `batch=${f.batch}`, `patience=${f.patience}`);
      if (this.isYamlModel && f.pretrained) {
        const w = this.weightChoices.find(c => c.value === f.pretrained);
        parts.push(`pretrained=${w ? w.label.replace(/ \(.*\)$/, "") : f.pretrained}`);
      }
      Object.entries(this.typedArgs).forEach(([k, v]) => parts.push(`${k}=${showValue(v)}`));
      return parts.join(" ");
    }
  },
  watch: {
    task() {
      this.pickFamily();
    },
    "form.family"() {
      this.pickVariant();
    },
    "form.kind"() {
      this.pickVariant();
    },
    openId(id) {
      this.watchLive(id);
      this.steps = { runId: id, points: [], total: 0 };
      if (id != null) this.loadSteps(id);
    },
    smoothing(v) {
      try {
        localStorage.setItem(SMOOTHING_KEY, String(v));
      } catch {
        // not kept
      }
    },
    weightChoices(list) {
      if (this.form.pretrained && !list.some(c => c.value === this.form.pretrained)) this.form.pretrained = "";
    }
  },
  methods: {
    async load() {
      this.loading = true;
      try {
        const [st, ex, md, cat, up] = await Promise.all([
          axios.get("/api/train/status"),
          axios.get("/api/train/exports"),
          axios.get("/api/model/yolo").catch(() => ({ data: { models: [] } })),
          axios.get("/api/train/catalog").catch(() => ({ data: { families: [], args: {} } })),
          axios.get("/api/train/uploads").catch(() => ({ data: { uploads: [] } }))
        ]);
        this.status = st.data;
        this.catalog = cat.data;
        this.exports = ex.data.exports || [];
        // only YOLO (.pt) models can be trained further, not MediaPipe ones
        this.models = (md.data.models || []).filter(m => m.name && m.framework !== "mediapipe");
        this.uploads = up.data.uploads || [];
        const wanted = Number(this.$route.query.export);
        if (wanted && this.exports.some(e => e.id === wanted)) this.form.export_id = wanted;
        else if (!this.chosenExport && this.exports.length) this.form.export_id = this.exports[0].id;
        if (!this.form.base_model && this.models.length) this.form.base_model = this.models[0].name;
        if (!this.form.upload_id && this.uploads.length) this.form.upload_id = this.uploads[0].id;
        this.pickFamily();
      } finally {
        this.loading = false;
      }
      await this.loadRuns();
    },
    pickFamily() {
      if (!this.families.some(f => f.key === this.form.family) && this.families.length) {
        this.form.family = this.families[0].key;
      }
      this.pickVariant();
    },
    /** keep the size when switching family / kind; else the smallest */
    pickVariant() {
      if (this.chosenVariant) return;
      const scale = (this.form.model.match(/^(?:yolov?\d+|rtdetr-)([a-z]\d?)/) || [])[1];
      const v =
        this.variants.find(i => scale && i.scale === scale && !/-p\d|-ghost|-cls-resnet/.test(i.name)) ||
        this.variants.find(i => i.scale === "n") ||
        this.variants[0];
      this.form.model = v ? v.name : "";
    },
    /** change one argument (from the augmentation list) in the table */
    editArg(key, value) {
      if (!(key in this.form.overrides)) this.form.overrides = { ...this.form.overrides, [key]: value };
      this.showAdvanced = true;
      this.$nextTick(() => this.$refs.argsTable && this.$refs.argsTable.focus(key));
    },
    fmtSize(bytes) {
      if (!bytes) return "0 B";
      const u = ["B", "KB", "MB", "GB"];
      const i = Math.min(u.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
      return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${u[i]}`;
    },
    extraText(extra) {
      return Object.entries(extra)
        .map(([k, v]) => `${k}=${showValue(typeof v === "string" && v.includes("/") ? v.split("/").pop() : v)}`)
        .join(" ");
    },
    async loadArgsFile(e) {
      const file = e.target.files[0];
      e.target.value = "";
      if (!file) return;
      const data = new FormData();
      data.append("file", file);
      try {
        const r = await axios.post("/api/train/parse-args", data);
        const args = r.data.args || {};
        let n = 0;
        Object.entries(args).forEach(([k, v]) => {
          n++;
          if (MAIN_ARGS.includes(k)) {
            this.form[k] = v;
            return;
          }
          this.form.overrides = { ...this.form.overrides, [k]: showValue(v) };
        });
        const ignored = (r.data.ignored || []).map(i => i.key);
        this.argsNote = this.$t("train.argsLoaded", { n }) + (ignored.length ? "；" + this.$t("train.argsIgnored", { list: ignored.join(", ") }) : "");
        this.showAdvanced = true;
      } catch (error) {
        const d = (error.response && error.response.data) || {};
        this.$toastr.error(d.message || String(error));
      }
    },
    async uploadModel(e) {
      const file = e.target.files[0];
      e.target.value = "";
      if (!file) return;
      const data = new FormData();
      data.append("file", file);
      this.uploadPct = 0;
      try {
        const r = await axios.post("/api/train/uploads", data, {
          onUploadProgress: p => (this.uploadPct = p.total ? Math.round((100 * p.loaded) / p.total) : 0)
        });
        this.$toastr.success(this.$t("train.uploaded", { name: r.data.name }));
        await this.loadUploads();
        this.form.upload_id = r.data.id;
      } catch (error) {
        const d = (error.response && error.response.data) || {};
        this.$toastr.error(d.message || String(error));
      } finally {
        this.uploadPct = null;
      }
    },
    async loadUploads() {
      const r = await axios.get("/api/train/uploads");
      this.uploads = r.data.uploads || [];
    },
    async removeUpload(u) {
      if (!confirm(this.$t("train.deleteUpload", { name: u.name }))) return;
      try {
        await axios.delete(`/api/train/uploads/${u.id}`);
        if (this.form.upload_id === u.id) this.form.upload_id = null;
        await this.loadUploads();
      } catch (error) {
        const d = (error.response && error.response.data) || {};
        this.$toastr.error(d.message || String(error));
      }
    },
    async loadRuns() {
      const r = await axios.get("/api/train/");
      this.runs = r.data.runs || [];
      if (this.openId != null) await this.loadDetail();
    },
    async loadDetail() {
      if (this.openId == null) return;
      const r = await axios.get(`/api/train/${this.openId}`);
      const atBottom = this.logAtBottom();
      this.detail = r.data;
      if (r.data.status === "running" && !this.live) this.loadSteps(r.data.id);
      if (atBottom) this.$nextTick(() => this.scrollLog());
    },
    logAtBottom() {
      const el = this.$refs.log && (Array.isArray(this.$refs.log) ? this.$refs.log[0] : this.$refs.log);
      return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    },
    scrollLog() {
      const el = this.$refs.log && (Array.isArray(this.$refs.log) ? this.$refs.log[0] : this.$refs.log);
      if (el) el.scrollTop = el.scrollHeight;
    },
    async poll() {
      try {
        const st = await axios.get("/api/train/status");
        this.status = st.data;
        if (this.runs.some(r => r.status === "running" || r.status === "queued") || this.openId != null) {
          await this.loadRuns();
        }
      } catch {
        // try again next time
      }
    },
    trainerOf(name) {
      return ((this.status && this.status.trainers) || []).find(t => t.name === name) || null;
    },
    /** offline / training #n / GPU used elsewhere / free */
    trainerState(tr) {
      if (!tr.alive) return this.$t("train.servers.offline");
      if (tr.run_id) return this.$t("train.servers.training", { id: tr.run_id });
      if (tr.gpu && tr.gpu.busy) return this.$t("train.servers.gpuElsewhere");
      return this.$t("train.servers.idle");
    },
    /** GPU memory and load, e.g. 9.0 / 16 GB · 97% */
    gpuUse(g) {
      const gb = mb => (mb / 1024).toFixed(mb >= 10240 ? 0 : 1);
      return `${gb(g.mem_used)} / ${gb(g.mem_total)} GB · ${g.util}%`;
    },
    trainerTitle(tr) {
      if (!tr.alive) return this.$t("train.servers.offlineHint");
      const lines = [];
      if (tr.gpu && tr.gpu.busy) lines.push(this.$t("train.servers.gpuElsewhereHint"));
      (tr.gpu && tr.gpu.procs ? tr.gpu.procs : []).forEach(p =>
        lines.push(`${p.name || "?"} (pid ${p.pid}) · ${(p.mem / 1024).toFixed(1)} GB`)
      );
      if (tr.version) lines.push("Ultralytics " + tr.version);
      return lines.join("\n");
    },
    /** where a run trains / trained / waits to */
    whereLabel(r) {
      const many = ((this.status && this.status.trainers) || []).length > 1;
      if (r.status === "queued") {
        // waiting for a GPU used outside this site
        const t = r.target ? this.trainerOf(r.target) : null;
        if (t && t.alive && !t.run_id && t.gpu && t.gpu.busy) {
          return "→ " + r.target + " · " + this.$t("train.servers.waitingGpu");
        }
        return r.target ? "→ " + r.target : "";
      }
      return many || (r.worker && r.worker !== "main") ? r.worker : "";
    },
    async toggleServers() {
      this.showServers = !this.showServers;
      if (this.showServers) await this.loadServers();
    },
    async loadServers() {
      const r = await axios.get("/api/worker/servers");
      this.servers = r.data.workers || [];
    },
    async addServer() {
      try {
        const r = await axios.post("/api/worker/servers", { name: this.newServer });
        this.setup = r.data;
        this.newServer = "";
        await Promise.all([this.loadServers(), this.poll()]);
      } catch (error) {
        const d = (error.response && error.response.data) || {};
        this.$toastr.error(d.message || String(error));
      }
    },
    async newToken(w) {
      if (!confirm(this.$t("train.servers.newTokenConfirm", { name: w.name }))) return;
      const r = await axios.post(`/api/worker/servers/${encodeURIComponent(w.name)}`);
      this.setup = r.data;
    },
    async removeServer(w) {
      if (!confirm(this.$t("train.servers.removeConfirm", { name: w.name }))) return;
      await axios.delete(`/api/worker/servers/${encodeURIComponent(w.name)}`);
      if (this.setup && this.setup.name === w.name) this.setup = null;
      await Promise.all([this.loadServers(), this.poll()]);
    },
    async copySetup() {
      try {
        await navigator.clipboard.writeText(this.setupScript);
        this.$toastr.success(this.$t("train.servers.copied"));
      } catch {
        // select it by hand
      }
    },
    async loadSteps(id) {
      try {
        const r = await axios.get(`/api/train/${id}/steps`);
        if (this.openId !== id) return;
        // points pushed meanwhile come after the ones of the answer
        const after = this.steps.runId === id ? this.steps.points.filter(p => !r.data.points.length || p.x > r.data.points[r.data.points.length - 1].x) : [];
        this.steps = { runId: id, points: r.data.points.concat(after), total: r.data.total + after.length };
      } catch {
        // no points
      }
    },
    /** follow the open run's output live over the socket (the page's poll
     *  still brings the status and the charts) */
    watchLive(id) {
      this.live = null;
      if (id == null) {
        this.$socket.emit("train_unwatch");
        return;
      }
      this.$socket.emit("train_watch", { run_id: id }, ack => {
        if (!ack || !ack.ok || this.openId !== id) return;
        const atBottom = this.logAtBottom();
        this.live = { runId: id, lines: ack.lines || [], progress: ack.progress || "" };
        if (atBottom) this.$nextTick(() => this.scrollLog());
      });
    },
    async toggle(r) {
      if (this.openId === r.id) {
        this.openId = null;
        this.detail = null;
        return;
      }
      this.openId = r.id;
      this.detail = null;
      await this.loadDetail();
      await this.$nextTick();
      this.scrollLog();
    },
    async start() {
      this.busy = true;
      try {
        const f = this.form;
        const extra = {};
        Object.assign(extra, this.typedArgs);
        if (this.isYamlModel && f.pretrained) extra.pretrained = f.pretrained;
        const body = { export_id: f.export_id, epochs: f.epochs, imgsz: f.imgsz, batch: f.batch, patience: f.patience, name: f.name, source: f.source, extra, target: f.target };
        if (f.source === "models") body.base_model = f.base_model;
        else if (f.source === "upload") body.upload_id = f.upload_id;
        else body.model = f.model;
        const r = await axios.post("/api/train/", body);
        this.$toastr.success(this.$t("train.queued", { id: r.data.id }));
        this.openId = r.data.id;
        await this.loadRuns();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      } finally {
        this.busy = false;
      }
    },
    /** fill the form with a past training's settings (model, numbers,
     *  arguments, where it trained), to train again or change a little */
    async reuse(run) {
      const p = run.params || {};
      const f = this.form;
      const notes = [];
      if (this.exports.some(e => e.id === run.export_id)) f.export_id = run.export_id;
      else notes.push(this.$t("train.reuseNoExport", { id: run.export_id }));
      const extra = { ...(p.extra || {}) };
      let pretrained = extra.pretrained;
      delete extra.pretrained;
      if (p.source === "upload" && this.uploads.some(u => u.id === p.upload_id)) {
        f.source = "upload";
        f.upload_id = p.upload_id;
      } else if ((p.source === "models" || p.base_model) && this.models.some(m => m.name === p.base_model)) {
        f.source = "models";
        f.base_model = p.base_model;
      } else {
        const name = p.source === "catalog" || !p.source ? p.model || (p.family ? `${p.family}${p.size || "n"}.pt` : "") : "";
        const fam = (this.catalog.families || []).find(x => x.items.some(i => i.name === name));
        if (fam) {
          f.source = "catalog";
          f.family = fam.key;
          f.kind = name.endsWith(".yaml") ? "yaml" : "pt";
          await this.$nextTick();
          f.model = name;
        } else {
          notes.push(this.$t("train.reuseNoModel", { name: p.label || p.model || "?" }));
        }
      }
      await this.$nextTick();
      // weights loaded into an architecture: an official name, or an upload
      if (typeof pretrained === "string") {
        const up = pretrained.match(/-u(\d+)\.pt$/);
        pretrained = up ? `upload:${up[1]}` : pretrained;
        f.pretrained = this.weightChoices.some(c => c.value === pretrained) ? pretrained : "";
      } else {
        f.pretrained = "";
      }
      ["epochs", "imgsz", "batch", "patience"].forEach(k => {
        if (p[k] != null) f[k] = p[k];
      });
      const overrides = {};
      Object.entries(extra).forEach(([k, v]) => (overrides[k] = showValue(v)));
      f.overrides = overrides;
      f.target = run.target && this.trainerOf(run.target) ? run.target : "";
      f.name = "";
      if (Object.keys(overrides).length) this.showAdvanced = true;
      this.$toastr.success(this.$t("train.reused", { id: run.id }) + (notes.length ? "；" + notes.join("；") : ""));
      this.$nextTick(() => this.$refs.newForm && this.$refs.newForm.scrollIntoView({ behavior: "smooth", block: "start" }));
    },
    async resume(r) {
      try {
        await axios.post(`/api/train/${r.id}/resume`);
        this.$toastr.success(this.$t("train.resumeQueued", { id: r.id }));
        await this.loadRuns();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      }
    },
    async stop(r) {
      if (r.status === "running" && !confirm(this.$t("train.stopConfirm"))) return;
      await axios.post(`/api/train/${r.id}/stop`);
      await this.loadRuns();
    },
    async remove(r) {
      if (!confirm(this.$t("train.removeConfirm", { id: r.id }))) return;
      try {
        await axios.delete(`/api/train/${r.id}`);
        if (this.openId === r.id) {
          this.openId = null;
          this.detail = null;
        }
        await this.loadRuns();
      } catch (error) {
        const data = (error.response && error.response.data) || {};
        this.$toastr.error(data.message || String(error));
      }
    },
    exportLabel(e) {
      const parts = [`#${e.id}`, e.datasets.join(" + "), this.$t("yolo." + e.task)];
      if (e.split) parts.push(`${e.split.train}/${e.split.val}/${e.split.test}`);
      if (e.augment) parts.push(this.$t("train.augmented"));
      parts.push(new Date(e.created_at).toLocaleString());
      return parts.join(" · ");
    },
    modelLabel(r) {
      const p = r.params || {};
      return p.label || p.base_model || (p.family && p.size ? `${p.family}${p.size}` : p.model);
    },
    pct(r) {
      if (r.status === "done") return 100;
      return r.epochs ? Math.min(100, Math.round((100 * r.epoch) / r.epochs)) : 0;
    },
    statusClass(s) {
      return { queued: "text-bg-secondary", running: "text-bg-primary", done: "text-bg-success", failed: "text-bg-danger", stopped: "text-bg-warning" }[s];
    },
    /** the headline number: mAP50-95 (boxes, masks or poses), else top-1 accuracy */
    mainMetricKey(row) {
      if (!row) return null;
      return Object.keys(row).find(k => /^metrics\/mAP50-95/.test(k)) || Object.keys(row).find(k => /accuracy_top1/.test(k)) || null;
    },
    mainMetric(row) {
      const key = this.mainMetricKey(row);
      if (!key) return "";
      const name = /accuracy/.test(key) ? "top-1" : "mAP50-95";
      return `${name} ${row[key].toFixed(3)}`;
    },
  },
  mounted() {
    this.load();
    let last = 0;
    this.timer = setInterval(async () => {
      if (document.hidden || this.ticking) return;
      this.ticking = true;
      try {
        if (Date.now() - last >= POLL_MS) {
          last = Date.now();
          await this.poll();
        } else if (this.detail && this.detail.status === "running" && !this.live) {
          await this.loadDetail();
        }
      } catch {
        // try again next time
      } finally {
        this.ticking = false;
      }
    }, LIVE_MS);
  },
  sockets: {
    train_log(data) {
      if (!this.live || data.run_id !== this.live.runId) return;
      const atBottom = this.logAtBottom();
      if (data.lines && data.lines.length) {
        const lines = this.live.lines.concat(data.lines);
        this.live.lines = lines.length > 1000 ? lines.slice(-1000) : lines;
      }
      this.live.progress = data.progress || "";
      if (data.steps && data.steps.length && this.steps.runId === data.run_id) {
        let points = this.steps.points.concat(data.steps);
        if (points.length > MAX_STEPS) points = thin(points);
        this.steps = { runId: data.run_id, points, total: this.steps.total + data.steps.length };
      }
      if (atBottom) this.$nextTick(() => this.scrollLog());
    },
    connect() {
      // a new socket: watch again
      if (this.openId != null) this.watchLive(this.openId);
    }
  },
  beforeUnmount() {
    clearInterval(this.timer);
    if (this.openId != null) this.$socket.emit("train_unwatch");
  }
};
</script>

<style scoped>
.page-container {
  text-align: left;
  max-width: 1200px;
  margin: 0 auto;
  padding-left: 16px;
  padding-right: 16px;
}
.trainer-pill {
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.85rem;
  font-weight: 600;
}
.trainer-pill.ok {
  background: #d1e7dd;
  color: #0f5132;
}
.trainer-pill.other {
  background: #ffe5d0;
  color: #8a3b00;
}
.trainer-pill .gpu-use {
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}
.trainer-pill.busy {
  background: #cfe2ff;
  color: #084298;
}
.server-name {
  max-width: 220px;
}
.trainer-pill.down {
  background: #fff3cd;
  color: #664d03;
}
.variants {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 150px;
  overflow: auto;
}
.variants .btn {
  font-family: Menlo, Consolas, monospace;
  font-size: 0.75rem;
  padding: 1px 6px;
}
.uploads {
  border: 1px solid #e9ecef;
  border-radius: 6px;
  max-height: 180px;
  overflow: auto;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  margin: 0;
  cursor: pointer;
  border-bottom: 1px solid #f1f3f5;
  min-width: 0;
}
.upload-row.on {
  background: #e7f1ff;
}
.aug-detail {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 6px 10px;
  background: #fff;
}
.best-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 14px;
  background: #fff8e1;
  border: 1px solid #ffe8a1;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.85rem;
}
.best-metric {
  font-variant-numeric: tabular-nums;
}
.smoothing {
  width: 140px;
}
.smoothing-value {
  width: 2.5em;
  font-variant-numeric: tabular-nums;
}
.command {
  background: #f1f3f5;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
.run {
  border-bottom: 1px solid #e9ecef;
}
.run:last-child {
  border-bottom: 0;
}
.run-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 2px;
}
.run-head:hover {
  background: #f8f9fa;
}
.run-name {
  flex: 1 1 auto;
  min-width: 0;
}
.run-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 200px;
  flex: none;
}
.run-progress .progress {
  flex: 1;
  display: flex;
}
.metric {
  /* "★ mAP50-95 0.387 @12": as wide as it needs, the name gives way */
  flex: none;
  min-width: 120px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.run-head > * {
  flex-shrink: 0;
}
.run-head > .run-name,
.run-head > .run-model {
  flex-shrink: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.run-head > .run-model {
  flex-shrink: 3;
}
.creator {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.run-body {
  padding: 4px 4px 12px;
}
.train-log {
  background: #1e1e1e;
  color: #d4d4d4;
  font-size: 0.75rem;
  border-radius: 6px;
  padding: 8px 10px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
/* phones: the run's name on its own line, progress and score below */
@media (max-width: 767.98px) {
  .run-head {
    flex-wrap: wrap;
    row-gap: 4px;
  }
  .run-head > .run-name {
    flex: 1 1 calc(100% - 110px);
  }
  .run-head > .run-model {
    order: 5;
    flex: 1 1 100%;
  }
  .run-progress {
    order: 6;
    flex: 1 1 140px;
    width: auto;
  }
  .run-head > .metric {
    order: 7;
    min-width: 0;
  }
  .run-head > .fa {
    order: 2;
  }
  .page-container {
    padding-left: 10px;
    padding-right: 10px;
  }
  .smoothing {
    width: 100px;
  }
}
</style>
