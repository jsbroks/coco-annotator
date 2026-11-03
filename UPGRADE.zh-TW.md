# coco-annotator 升級說明（繁體中文）

完整英文版見 [UPGRADE.md](UPGRADE.md)。

## 升級了什麼

| 項目 | 原本 | 現在 |
|---|---|---|
| 前端 | Vue 2.5 + Vue CLI 3（webpack 4）、Node 10 | **Vue 3.5 + Vite 7**、Node 22 |
| 後端 | Python 3.6、Flask 1.0、flask-restplus（已停止維護） | **Python 3.12、Flask 3.1、flask-restx** |
| 即時通訊 | Flask-SocketIO 3 + eventlet | Flask-SocketIO 5（threading 模式） |
| 背景任務 | Celery 4.2 | Celery 5.5 |
| 資料庫 | MongoDB 4.0 | **MongoDB 7.0**（需要遷移，見下方） |
| AI 輔助 | DEXTR + Mask R-CNN（TensorFlow 1.14） | **Segment Anything（PyTorch）** |
| 介面框架 | Bootstrap 4 + jQuery | **Bootstrap 5.3**（不再使用 jQuery） |

## 新功能

### 旋轉物件框（快捷鍵 `O`）

先選取一個標註，切到「Rotated BBox」工具（斜放的方框圖示），用三下點擊畫框：

1. 點第一個角
2. 點第二個角：這兩點就是框的一條邊，決定方向和長度（也可以從第一點直接拖到第二點；按住 **Shift** 會吸附到 15° 的倍數）
3. 移動滑鼠拉出寬度，再點一下完成（按 **Esc** 取消）

畫好的框可以這樣編輯：拖曳圓形把手旋轉（按住 **Shift** 吸附角度）、拖曳角落縮放（對角固定不動）、在框內拖曳移動。

也可以像 BBox 一樣用**選取工具**（`S`）編輯：在框內拖曳移動、拖曳角落縮放（維持角度與矩形），點邊線不會新增點。用旋轉框工具時，方向鍵可微調位置（1 px，Shift 為 10 px）。

使用旋轉框工具時，在畫面上點另一個旋轉框會選取它；要在既有的框裡面開始畫新框，按住 `Ctrl` 再點。使用 SAM 工具時，點到既有的標註不會切換選取，要選其他標註請點右側清單或按 `S` 切到選取工具。

較粗的那條邊代表框的「朝向」（第一條邊）。

匯出格式：

```json
"isrbbox": true,
"rbbox": [cx, cy, w, h, angle],
"segmentation": [[x1, y1, x2, y2, x3, y3, x4, y4]]
```

`angle` 單位為度，在影像座標（y 向下）中順時針為正，沿第一條邊（角點 1→2）量測。
`segmentation` 依序存 4 個角點，所以只認一般 COCO 多邊形的工具也能讀。

轉成訓練格式：

```bash
python scripts/export_obb.py coco-export.json labels/ --format dota       # DOTA
python scripts/export_obb.py coco-export.json labels/ --format yolo-obb   # Ultralytics YOLO-OBB
```

### Segment Anything（快捷鍵 `A`）

先選取一個標註，切到「SAM」工具（◎ 圖示）：

- 點物體（綠點），**Shift**+點擊排除背景（紅點），或拖曳框住物體
- 按 **Enter**（或面板上的 Apply）把預覽加入標註

切換到 SAM 工具時伺服器就會先算好該圖的 embedding，之後每次點擊約 50 ms。

啟用方式：

```bash
./models/download_sam.sh                       # 下載 vit_b 權重到 ./models
SAM=cpu docker compose up -d --build           # CPU 版
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build   # NVIDIA GPU 版
```

沒裝 PyTorch 或沒有權重檔時，SAM 工具會自動停用，不影響其他功能。

### 用自己訓練的 YOLO 模型預標註

把訓練好的 Ultralytics YOLO 權重檔（`.pt`，YOLOv8 / YOLO11 以後的版本）複製到 `models/` 資料夾（可以放在子資料夾）。支援四種模型：

| 模型類型 | 產生的標註 |
|---|---|
| detect | 物件框（BBox） |
| obb | 旋轉框 |
| segment | 多邊形 |
| pose | 物件框 + 關鍵點 |

需要用 `SAM=cpu` 或 `SAM=cuda` 建置的映像檔（和 SAM 共用 PyTorch）。

- **標一張圖：** 標註畫面左側工具列的火箭按鈕。會先儲存目前的進度，再執行模型，預測結果會變成一般的標註，可以再修改。
- **整個資料集：** 資料集頁面左側的「用模型預標註」。在背景執行，進度顯示在「任務」頁面；可以選擇略過已經有標註的圖片。

管理員也可以直接在這個視窗上傳或移除模型：選 `.pt` 檔按「上傳」，伺服器會先試著載入，確認是可用的 YOLO 模型才會加入清單。

模型的類別會依名稱（不分大小寫）對應到資料集的類別，缺少的類別可以自動建立。pose 模型：如果類別還沒設定關鍵點名稱，會自動從模型帶入（17 個點的模型會用 COCO 的人體關鍵點和骨架）；信心低於 0.5 的關鍵點會標成「未標註」。

放進新的 `.pt` 檔不需要重啟。注意：載入 `.pt` 檔會執行檔案裡的程式，只放你信任來源的模型。

### 清除這張圖片的標註

標註畫面左側工具列的 ⊗ 按鈕（或按 D）會刪除目前這張圖片的全部標註，不用確認，按 Ctrl+Z 可以復原。刪除的標註會放進「活動紀錄」的垃圾桶，90 天內都可以救回。

## 從舊版升級：一定要做的事

**MongoDB 資料遷移**：新版的資料存在 `mongodb7_data` volume。舊版的 `mongodb_data`（MongoDB 4.0，MongoDB 7 無法直接開啟）完全不會被動到，所以隨時可以退回舊版。在服務停止的狀態下，把資料複製過來一次即可：

```bash
cd coco-annotator             # 你執行 docker compose 的資料夾
docker compose down
git fetch && git checkout upgrade-2026
./scripts/migrate_mongo.sh    # 自動找到舊 volume，備份後還原到 mongodb7_data
docker compose up -d --build
```

腳本只會備份應用程式的資料庫（`flask`），並在 `mongo-dump-*/` 留一份備份檔，完成後會列出各資料表的筆數。如果舊服務還在執行，腳本會拒絕執行。如果它無法判斷哪個是舊 volume（例如資料夾改過名，或當初是用舊版 `docker-compose` v1 啟動，名稱會是 `cocoannotator_mongodb_data`），就手動指定：`OLD_VOLUME=名稱 ./scripts/migrate_mongo.sh`。

如果舊版是用原本的 `docker-compose.gpu.yml` 啟動，資料庫不在 volume，而是在專案旁的 `db/` 資料夾，改用：`OLD_DIR=舊專案路徑/db ./scripts/migrate_mongo.sh`。

也可以把新版裝在另一個資料夾、舊資料夾完全不動：在 `.env`（參考 `.env.example`）設定 `DATASETS_DIR` 指向舊的 `datasets` 資料夾，兩個版本就會共用同一批圖片。

**退回舊版**：`docker compose down`，切回原本的程式碼（`git checkout master`），再 `docker compose up -d`，就會用回舊的 volume。`datasets/` 裡的圖片兩個版本共用，不會被修改。

其他注意事項：

- 舊帳號密碼照常可登入，第一次登入時會自動轉成新的雜湊格式
- 已移除的環境變數：`MASK_RCNN_FILE`、`MASK_RCNN_CLASSES`、`DEXTR_FILE`
- 已移除的功能：Google 圖片自動下載（該套件多年前就已失效）
- 「Annotate Image」按鈕（串接外部模型伺服器）仍保留
- 關閉公開註冊：在 `.env` 加上 `ALLOW_REGISTRATION=false`，再執行 `docker compose up -d`。之後只有管理員能在「Admin」頁面建立帳號（導覽列的 Admin 連結只在寬螢幕顯示，也可以直接開 `/#/admin/panel`）

## 順便修掉的原專案 bug

- 多執行緒下 Celery 任務會被送到錯誤的 broker（掃描、匯入、匯出都會失效）
- 檔案監看器遇到寫到一半的圖片就整個停止
- 標註畫面按 Esc 會報錯
- `FILE_WATCHER=false` 實際上會被當成開啟
- 匯出檔名出現 `b'...'`
- 幾個參照不存在變數或 model 的錯誤

## 自動儲存

標註的修改（形狀、關鍵點、附加資訊）會在停止操作約 2 秒後自動存到伺服器；關閉分頁、重新整理或切到別的分頁時，也會先把還沒存的部分送出。原本只有按儲存、切換圖片或離開頁面時才會存。

## 介面語言

介面提供 English 和繁體中文。在導覽列右上角的地球圖示選單切換，選擇會記在瀏覽器裡；第一次開啟時依瀏覽器語言決定，任何中文都會選繁體中文。

翻譯檔在 `client/src/i18n/locales/*.json`（vue-i18n）。要新增其他語言：複製 `en.json` 翻譯後，在 `client/src/i18n/index.js` 的 `LANGUAGES` 加上一筆即可。伺服器回傳的錯誤訊息目前仍是英文。

## 關鍵點

選取的標註必須先有 BBox 或旋轉框，關鍵點工具才會啟用：先畫出物件的框，再標關鍵點。

## Bootstrap 5

介面已從 Bootstrap 4 + jQuery 升級為 Bootstrap 5.3，不再使用 jQuery。`client/src/assets/bootstrap-compat.css` 讓畫面維持和原本一樣的外觀。如果你自己改過模板，`data-toggle` 等屬性要改成 `data-bs-*`，部分 class 名稱也有改變（例如 `mr-2` → `me-2`、`btn-block` → `w-100`）。
