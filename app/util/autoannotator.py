import threading
import Queue
import cv2
import np
from models import ImageModel, AnnotationModel
from skimage.measure import compare_ssim

annotations_queue = Queue.Queue(maxsize=32)


def submit(segmentation, category_id, prev_segmentation=None):
    """
    """


def start():
    """
    """
    global autoanotator_thread
    autoanotator_thread = threading.Thread(target=propagate_annotations)


def stop():
    """
    """
    global autoanotator_thread
    annotations_queue.close()
    autoanotator_thread.join()


def segmentation_equal(seg_a, seg_b):
    if len(seg_a) != len(seg_b):
        return False
    for i in range(len(seg_a)):
        if len(seg_a[i]) != len(seg_b[i]):
            return False
        for j in range(len(seg_a[i])):
            if seg_a[i][j] != seg_b[i][j]:
                return False
    return True


def extract_patch(segmentation, img):
    mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
    mask = cv2.drawContours(mask, segmentation, -1, 255, -1)
    return cv2.bitwise_and(img, img, mask=mask)


def propagate_annotations():
    """
    """
    while True:
        annotation_id = annotations_queue.get()
        if annotation_id is None:
            break
        
        annotation = AnnotationModel.objects(id=annotation_id).first()
        image_from = ImageModel.objects(id=annotation.image_id).first()
        img = cv2.imread(image_from.path)
        mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        mask = cv2.drawContours(mask, annotation.segmentation, -1, 255, -1)
        patch = cv2.bitwise_and(img, img, mask=mask)

        dataset_id = image_from.dataset_id
        images = list(ImageModel.objects(
            dataset_id=dataset_id, deleted=False).all())
        # test all other images in the same dataset
        for image_to in images:
            # skip images of different size
            if image_to.width != image_from.width \
            or image_to.height != image_from.height:
                continue
            cvimg = cv2.imread(image_to.path)
            img_patch = cv2.bitwise_and(cvimg, cvimg, mask=mask)
            score, _ = compare_ssim(
                patch, img_patch, full=True, multichannel=True)
            if score < 0.95:
                continue
            image_to.copy_annotations(
                AnnotationModel.objects(id=annotation_id))
            # copy the annotation to this image
