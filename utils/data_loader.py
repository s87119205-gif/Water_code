## author: xin luo, 
## created: 2023.10.14; modify: 
## des: data augmentation for multiscale patches

import torch
import random
from torchvision.transforms import v2
import torchvision.transforms.v2.functional as F


## build custom transforms
class GaussianNoise(v2.Transform):
    def __init__(self, mean = 0.0, sigma_max=0.1, p=0.5):
        super().__init__()
        self.mean = mean
        self.sigma_max = sigma_max
        self.p = p
    def transform(self, inpt, params):  # rewrite transform function to update sigma
        patch, ptruth = inpt[0:-1], inpt[-1:]
        if torch.rand(1) < self.p:
            self.sigma = torch.rand(1)*self.sigma_max  ## update sigma        
            noise_patch = torch.randn_like(patch) * self.sigma            
            patch = patch + noise_patch
            inpt = torch.cat([patch, ptruth], dim=0)
        return inpt


class SceneArraySet(torch.utils.data.Dataset):
    '''
    des: scene and truth image reading from the np.array(): read data from memory.
    '''
    def __init__(self, scene_truth_list, transforms=None):
        '''input arrs_scene, arrs_truth are list'''
        self.scene_truth_list = scene_truth_list
        self.transforms = transforms
    def __getitem__(self, index):
        '''load images and truths'''
        scene_truth = self.scene_truth_list[index]
        '''pre-processing (e.g., random crop)'''
        ### Image augmentation
        if self.transforms is not None:
            scene_truth = self.transforms(scene_truth)
        patches, ptruth = scene_truth[0:-1], scene_truth[-1:]
        return patches, ptruth
    def __len__(self):
        return len(self.scene_truth_list) 

class PatchPathSet(torch.utils.data.Dataset):
    def __init__(self, paths_valset, transforms=None):
        self.paths_patch_ptruth = paths_valset
        self.transforms = transforms
    def __getitem__(self, index):
        '''load patches and truths'''
        patches_truth = torch.load(self.paths_patch_ptruth[index], 
                                   weights_only=False)        
        if self.transforms is not None:
            patches_truth = self.transforms(patches_truth)
        patches = patches_truth[0:-1]
        truth = patches_truth[-1:]
        return patches, truth
    def __len__(self):
        return len(self.paths_patch_ptruth)

