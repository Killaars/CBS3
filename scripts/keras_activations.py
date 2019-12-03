#%%
from keras.models import load_model
from keract import get_activations, display_activations, display_heatmaps
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
#%%
path = Path("/home/killaarsl/Documents/racebaandemo/ADR")


model = load_model(str(path / "tempmodel.h5"))
image = plt.imread(str(path / "434_4_2.png"))
image = image[:,:,:3]
image = np.expand_dims(image, axis=0)




activations = get_activations(model, image )

#%%
display_activations(activations, cmap="gray", save=True)

#%%
display_heatmaps(activations, image, save=False)