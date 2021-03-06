"""
This module contains the logic to estimate the pose of the duckie relative to a circle pattern from an image
"""
from typing import Optional, Tuple

import cv2
import numpy as np


class PoseEstimator:
    """
    Object that handle the pose estimation logic
    """
    def __init__(self,
                 min_area: int,
                 min_dist_between_blobs: int,
                 height: int,
                 width: int,
                 circle_pattern_dist: float,
                 target_distance: float,
                 camera_mode: int):
        """
        Initialize PoseEstimator
        Args:
            min_area: minimum area of blob to be detected
            min_dist_between_blobs: minimum space between blob
            height: number of rows in circle pattern
            width: number of columns in circle pattern
            circle_pattern_dist: distance between circles in pattern
            target_distance: target goal to bumper
            camera_mode: int from 0 to 3, temp solution for debugging
        """
        params = cv2.SimpleBlobDetector_Params()
        params.minArea = min_area
        params.minDistBetweenBlobs = min_dist_between_blobs
        self.detector = cv2.SimpleBlobDetector_create(params)
        self.circle_pattern_dist = circle_pattern_dist
        self.height = height
        self.width = width
        self.circle_pattern = self._calc_circle_pattern()
        self.target_distance = target_distance
        self.camera_matrix = None
        self.distortion_coefs = None
        self.initialize_camera_matrix(camera_mode)
        self.counter = 0

    def initialize_camera_matrix(self, camera_mode: int):
        """
        Temporary methods to try different values for camera matrix and distortion coefs
        Args:
            camera_mode: int from 0 to 4 to choose from the 5 options
        """
        # TODO find the best mode and always use it.
        # camera matrix and distortion_coefs should be given as arguments to the constructor if available instead
        # of being hardcoded here. Same thing for image width and height
        camera_matrix = np.array([305.5718893575089, 0, 303.0797142544728,
                                  0, 308.8338858195428, 231.8845403702499,
                                  0, 0, 1]).reshape((3, 3))
        distortion_coefs = np.array([-0.2, 0.0305, 0.0005859930422629722, -0.0006697840226199427, 0]).reshape((1, 5))
        new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(camera_matrix, distortion_coefs, (640, 480), 0)

        if camera_mode == 0:
            self.camera_matrix = new_camera_matrix
            self.distortion_coefs = np.array([0., 0., 0., 0., 0.]).reshape((1, 5))
        elif camera_mode == 1:
            self.camera_matrix = new_camera_matrix
            self.distortion_coefs = distortion_coefs
        elif camera_mode == 2:
            self.camera_matrix = camera_matrix
            self.distortion_coefs = np.array([0., 0., 0., 0., 0.]).reshape((1, 5))
        elif camera_mode == 3:
            self.camera_matrix = camera_matrix
            self.distortion_coefs = distortion_coefs
        elif camera_mode == 4:
            self.camera_matrix = np.array([307.7379294605756, 0, 329.692367951685,
                                          0, 314.987773443905, 244.4605588877848,
                                          0, 0, 1]).reshape((3, 3))
            self.distortion_coefs = np.array(
                [-0.2565888993516047, 0.04481160508242147, -0.00505275149956019, 0.00130856936797665, 0]).reshape(
                (1, 5))

    def get_pose(self, obs: np.array) -> Tuple[bool, Optional[Tuple[np.array, float]]]:
        """
        Estimate a pose relative to a circle pattern, given an image
        Args:
            obs: input image in form of np.array

        Returns:
            a bool (True if pattern is detected), and a tuple([y, z, x], theta)
        """
        detection, centers = cv2.findCirclesGrid(obs,
                                                 patternSize=(self.width, self.height),
                                                 flags=cv2.CALIB_CB_SYMMETRIC_GRID,
                                                 blobDetector=self.detector)

        if detection:
            image_points = centers[:, 0, :]
            _, rotation_vector, translation_vector = cv2.solvePnP(objectPoints=self.circle_pattern,
                                                                  imagePoints=image_points,
                                                                  cameraMatrix=self.camera_matrix,
                                                                  distCoeffs=self.distortion_coefs)

        else:
            return detection, None
        theta = rotation_vector[1][0]
        x_bumper = translation_vector[0][0]
        y_bumper = translation_vector[2][0]

        y_target = y_bumper - self.target_distance * np.cos(theta)
        x_target = x_bumper + self.target_distance * np.sin(theta)

        return detection, (np.array([y_target, 0, x_target]), -np.rad2deg(theta))

    def _calc_circle_pattern(self):
        """
        Calculates the physical locations of each dot in the pattern.
        """
        circle_pattern_dist = self.circle_pattern_dist
        circle_pattern = np.zeros([self.height * self.width, 3])
        for i in range(self.width):
            for j in range(self.height):
                circle_pattern[i + j * self.width, 0] = circle_pattern_dist * i - \
                    circle_pattern_dist * (self.width - 1) / 2
                circle_pattern[i + j * self.width, 1] = circle_pattern_dist * j - \
                    circle_pattern_dist * (self.height - 1) / 2
        return circle_pattern
