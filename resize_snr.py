import numpy as np
import cv2
import sys
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from stereo_msgs.msg import DisparityImage
from ament_index_python.packages import get_package_share_directory
import message_filters
import math
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, HistoryPolicy, QoSDurabilityPolicy
import time
import os
from rclpy.executors import MultiThreadedExecutor
import threading

left_raw_list, right_raw_list = [],[]

class ImageResize(Node):
    def __init__(self):
        super().__init__("ImageResize")

        threading.Thread(target=self.resize_pub_callback).start()
        # threading.Thread(target=self.resizer_pub_callback).start()

        self.bridge = CvBridge()
        self.i = 1
        qos_policy = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_ALL,
                                depth=20,
                                durability=QoSDurabilityPolicy.VOLATILE)
        
        self.resizel_sub = message_filters.Subscriber(self, Image, "/left/image_raw", qos_profile=qos_policy)
        self.resizer_sub = message_filters.Subscriber(self, Image, "/right/image_raw", qos_profile=qos_policy)

        sync_resize = message_filters.ApproximateTimeSynchronizer(
        [self.resizel_sub, self.resizer_sub],
        queue_size=200,
        slop=0.05,
        allow_headerless=False)
        sync_resize.registerCallback(self.sync_resize_callback)

        self.resizel_publish = self.create_publisher(Image, 'left/image_resize', 20)
        self.resizer_publish = self.create_publisher(Image, 'right/image_resize', 20)
        # publish frequency -> model input? receive frequency?
        self.timerl = self.create_timer(0.1, self.resize_pub_callback)
        self.timerr = self.create_timer(0.1, self.resize_pub_callback)

    def sync_resize_callback(self, resizel_sub, resizer_sub):
        ros_time = rclpy.clock.Clock().now().to_msg()
        resizel_sub.header.stamp = ros_time
        resizel_sub.header.stamp = ros_time
       
        if resizel_sub.header.frame_id == "left_camera":
            self.left_raw = self.bridge.imgmsg_to_cv2(resizel_sub, "bgr8")
            left_raw_list.append(self.left_raw)
            
        if resizer_sub.header.frame_id == "right_camera":
            self.right_raw = self.bridge.imgmsg_to_cv2(resizer_sub, "bgr8")
            right_raw_list.append(self.right_raw)
            

    def resize_pub_callback(self):
        
        height = 400
        width = 600

        for self.left_image_raw, self.right_image_raw in zip(left_raw_list, right_raw_list):
                
            image_resizel = cv2.resize(self.left_image_raw, (width,height), interpolation=cv2.INTER_LINEAR)
            image_resizer = cv2.resize(self.right_image_raw, (width,height), interpolation=cv2.INTER_LINEAR)
            # (B, G, R) = cv2.split(image_resize)
            # bayer = np.empty((height, width), np.uint8)
            # # strided slicing for this pattern:
            # #   G R
            # #   B G
            # bayer[0::2, 0::2]= G[0::2, 0::2] # top left
            # bayer[1::2, 0::2]= R[1::2, 0::2] # top right
            # bayer[0::2, 1::2]= B[0::2, 1::2] # bottom left
            # bayer[1::2, 1::2]= G[1::2, 1::2] # bottom right
            
            # cv2.imshow("Resize_left", image_resizel)
            # cv2.imshow("Resize_right", image_resizer)
            # cv2.waitKey(1)
            self.get_logger().info(f'Resized_left_raw_image-{image_resizel.shape}: {self.i}')
            self.i += 1

            ros_time = rclpy.clock.Clock().now().to_msg()
            resizel_msg = self.bridge.cv2_to_imgmsg(np.array(image_resizel), 'bgr8')
            resizel_msg.header.frame_id = "left_camera"
            resizel_msg.header.stamp = ros_time
            resizer_msg = self.bridge.cv2_to_imgmsg(np.array(image_resizer), 'bgr8')
            resizer_msg.header.frame_id = "right_camera"
            resizer_msg.header.stamp = ros_time

            self.resizel_publish.publish(resizel_msg)
            self.resizer_publish.publish(resizer_msg)

            left_raw_list.clear()
            right_raw_list.clear()


def main(args=None):
    rclpy.init(args=args)
    try:
        resize_publisher = ImageResize()
        executor = MultiThreadedExecutor()
        executor.add_node(resize_publisher)

        try:
            executor.spin()
            # torch.cuda.empty_cache()
        finally:
            executor.shutdown()
            resize_publisher.destroy_node()
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()