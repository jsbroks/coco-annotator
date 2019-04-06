from dextr import DEXTR
from config import Config


model = DEXTR(nb_classes=1, resnet_layers=101, input_shape=(512, 512), weights_path=Config.DEXTR_FILE,
              num_input_channels=4, classifier='psp', sigmoid=True)
