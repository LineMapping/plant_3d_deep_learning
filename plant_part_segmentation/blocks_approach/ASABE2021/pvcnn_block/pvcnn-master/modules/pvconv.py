import torch.nn as nn
import torch
import modules.functional as F
from modules.voxelization import Voxelization
from modules.shared_mlp import SharedMLP
from modules.se import SE3d

__all__ = ['PVConv']


class PVConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, resolution, with_se=False, normalize=True, eps=0):
        super().__init__()
        self.in_channels = in_channels
        out_channels = out_channels//2

        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.resolution = resolution

        self.voxelization = Voxelization(resolution, normalize=normalize, eps=eps)
        voxel_layers = [
            nn.Conv3d(in_channels, out_channels, kernel_size, stride=1, padding=kernel_size // 2),
            nn.BatchNorm3d(out_channels, eps=1e-4),
            nn.LeakyReLU(0.1, True),
            nn.Conv3d(out_channels, out_channels, kernel_size, stride=1, padding=kernel_size // 2),
            nn.BatchNorm3d(out_channels, eps=1e-4),
            nn.LeakyReLU(0.1, True),
         ]
        if with_se:
            voxel_layers.append(SE3d(out_channels))
        self.voxel_layers = nn.Sequential(*voxel_layers)
        self.point_features = SharedMLP(in_channels, out_channels)

    def forward(self, inputs):

        #print("**************************************************************************** self.in_channels", self.in_channels)


        features, coords = inputs
        #print('coords.shape:',coords.shape, 'features.shape',features.shape)

        voxel_features, voxel_coords = self.voxelization(features, coords)

        #print('voxel_coords.shape:',voxel_coords.shape, 'voxel_features:',voxel_features.shape)

        voxel_features = self.voxel_layers(voxel_features)
        voxel_features = F.trilinear_devoxelize(voxel_features, voxel_coords, self.resolution, self.training)
        #print("*******************************************************************",voxel_features.shape)
        fused_features = torch.cat((voxel_features, self.point_features(features)),1) # voxel_features + self.point_features(features)
        #print("**********************************************************************", fused_features.shape)
        return fused_features, coords
