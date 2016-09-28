import numpy as np
from PIL import Image
import png
import matplotlib.pyplot as plt
from scipy import misc


class Haze(object):

    def __init__(self):
        self.focal_length = 1
        self.baseline = 1
        self.beta = 2
        self.height = 0
        self.width = 0
        self.haze_intensity = 200
        self.noise_variance = 10
        self.noise_mean = 0
        self.infinite_far = 1
        self.left = None
        self.right = None
        self.disp_left = None
        self.disp_right = None
        self.alpha_left = None
        self.alpha_right = None
        self.rain_left = None
        self.rain_right = None
        self.haze_map = None
        self.noisy_haze_map = None
        self.rendered_haze_left = None
        self.rendered_haze_right = None
        self.rendered_rain_left = None
        self.rendered_rain_right = None
        self.haze_rain_left_map = None
        self.haze_rain_right_map = None
        self.haze_file_left = 'out/render_haze_left.png'
        self.haze_file_right = 'out/render_haze_right.png'
        self.rain_file_left = 'out/render_rain_left.png'
        self.rain_file_right = 'out/render_rain_right.png'
        self.haze_rain_left = 'out/haze_rain_left.png'
        self.haze_rain_right = 'out/haze_rain_right.png'
        self.read_background_map()
        self.read_disparity_map(mode='pfm')

    def set_alpha_param(self, focal_length, baseline):
        self.focal_length = focal_length
        self.baseline = baseline

    def set_haze_intensity(self, intensity):
        self.haze_intensity = intensity

    def set_noise_param(self, mean, variance):
        self.noise_mean = mean
        self.noise_variance = variance

    def set_beta(self, beta_value):
        self.beta = beta_value

    def set_depth_param(self, infinite_far):
        self.infinite_far = infinite_far

    def set_haze_output(self, file_left, file_right):
        self.haze_file_left = file_left
        self.haze_file_right = file_right

    def set_rain_output(self, file_left, file_right):
        self.rain_file_left = file_left
        self.rain_file_right = file_right

    def set_all_output(self, file_left, file_right):
        self.haze_rain_left = file_left
        self.haze_rain_right = file_right

    def read_disparity_map(self, mode='pfm'):
        if mode == 'pfm':
            self.disp_left = self.read_disp_pfm('data/disp_left.pfm')
            self.disp_right = self.read_disp_pfm('data/disp_right.pfm')
        else:
            self.disp_left = self.read_disp_png('data/disp_left.png')
            self.disp_right = self.read_disp_png('data/disp_right.png')

    def read_background_map(self):
        self.left = self.read_image('data/left0.png')
        self.right = self.read_image('data/right0.png')
        # sanity check
        if self.left.shape == self.right.shape:
            (self.height, self.width) = self.left.shape[0:2]
        else:
            raise AssertionError

    def read_haze(self):
        haze = np.ones((self.height, self.width), dtype=np.float32)
        self.haze_map = haze * self.haze_intensity

    def get_depth_map(self, disparity_map):
        mask = (disparity_map == 0)
        disparity_map[mask] = self.infinite_far
        depth_map = self.focal_length * self.baseline / disparity_map
        return depth_map

    def get_alpha_map(self):
        depth_left = self.get_depth_map(self.disp_left.astype(np.float32))
        depth_right = self.get_depth_map(self.disp_right.astype(np.float32))
        self.alpha_left = np.exp(-1 * self.beta * depth_left)
        self.alpha_right = np.exp(-1 * self.beta * depth_right)

    def read_rain(self):
        self.rain_left = np.array(Image.open('data/rain_left.png'))
        self.rain_right = np.array(Image.open('data/rain_right.png'))

    def synthesize_rain(self):
        self.read_rain()
        self.rendered_rain_left = self.render_rain(self.left, self.rain_left)
        self.rendered_rain_right = self.render_rain(self.right, self.rain_right)
        self.write_image(self.rendered_rain_left, self.rain_file_left)
        self.write_image(self.rendered_rain_left, self.rain_file_right)

    def synthesize_haze(self):
        self.read_haze()
        self.add_noise()
        self.get_alpha_map()
        self.rendered_haze_left = self.render_haze(self.alpha_left, self.left, self.noisy_haze_map)
        self.rendered_haze_right = self.render_haze(self.alpha_right, self.right, self.noisy_haze_map)
        self.write_image(self.rendered_haze_left, self.haze_file_left)
        self.write_image(self.rendered_haze_right, self.haze_file_right)

    def synthesize_all(self):
        self.read_rain()
        self.get_alpha_map()
        self.read_haze()
        self.add_noise()
        haze_left = self.render_haze(self.alpha_left, self.left, self.noisy_haze_map)
        haze_right = self.render_haze(self.alpha_right, self.right, self.noisy_haze_map)
        self.haze_rain_left_map = self.render_rain(haze_left, self.rain_left)
        self.haze_rain_right_map = self.render_rain(haze_right, self.rain_right)
        self.write_image(self.haze_rain_left_map, self.haze_rain_left)
        self.write_image(self.haze_rain_right_map, self.haze_rain_right)

    @staticmethod
    def visualize(img):
        plt.imshow(img)
        plt.show()

    @staticmethod
    def read_image(image_file):
        img = Image.open(image_file)
        img_array = np.array(img, dtype=np.uint8)
        return img_array

    @staticmethod
    def write_image(image_map, filename):
        img = Image.fromarray(image_map)
        img.save(filename)

    @staticmethod
    def render_haze(alpha_map, background_map, haze_map):
        render_map = np.zeros(background_map.shape)
        render_map[:, :, 0] = alpha_map * background_map[:, :, 0] + (1 - alpha_map) * haze_map
        render_map[:, :, 1] = alpha_map * background_map[:, :, 1] + (1 - alpha_map) * haze_map
        render_map[:, :, 2] = alpha_map * background_map[:, :, 2] + (1 - alpha_map) * haze_map
        return render_map.astype(np.uint8)

    @staticmethod
    def read_disp_png(disp_file):
        """
        Read kitti disp from .png file
        :param disp_file:
        :return:
        """
        image_object = png.Reader(filename=disp_file)
        image_direct = image_object.asDirect()
        image_data = list(image_direct[2])
        (w, h) = image_direct[3]['size']
        channel = len(image_data[0]) / w
        disp = np.zeros((h, w, channel), dtype=np.uint16)
        for i in range(len(image_data)):
            for j in range(channel):
                disp[i, :, j] = image_data[i][j::channel]
        return disp[:, :, 0] / 256

    @staticmethod
    def read_disp_pfm(disp_file):
        import pfm
        (data, scale) = pfm.readPFM(disp_file)
        return data

    @staticmethod
    def render_rain(background_map, rain_map):
        bg = background_map.astype(np.uint16)
        r = rain_map.astype(np.uint16)
        rendered_map = np.clip(bg + r, 0, 255).astype(np.uint8)
        return rendered_map

    @staticmethod
    def write_flow(image_map, filename):
        f = open(filename, 'wb')
        magic = np.array([202021.25], dtype=np.float32)
        (height, width) = image_map.shape
        w = np.array([width], dtype=np.int32)
        h = np.array([height], dtype=np.int32)
        empty_map = np.zeros((height, width), dtype=np.float32)
        data = np.dstack((image_map, empty_map))
        magic.tofile(f)
        w.tofile(f)
        h.tofile(f)
        data.tofile(f)
        f.close()

    def add_noise(self):
        self.noisy_haze_map = self.haze_map + self.noise_variance * np.random.random(self.haze_map.shape)
