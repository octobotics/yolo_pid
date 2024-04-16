#!/usr/bin/env python3
import rospy
from ultralytics_ros.msg import YoloResult
from geometry_msgs.msg import Twist
from vision_msgs.msg import Detection2DArray
from geometry_msgs.msg import PoseStamped
import tf
import numpy as np

class AIControlNode:
    def __init__(self):
        rospy.init_node('ai_control_node', anonymous=True)

        rospy.Subscriber('/zed2i/zed_node/pose', PoseStamped, self.pose_callback)
        rospy.Subscriber('/yolo_result', YoloResult, self.yolo_result_callback)

        self.cmd_vel_pub = rospy.Publisher('/skid_steer/cmd_vel', Twist, queue_size=10)

        self.home_orientation = 0.0
        self.Kp = 0.5
        self.Ki = 0.0
        self.Kd = 0.1
        self.prev_error = 0.0
        self.integral = 0.0

        self.image_width = 1024

    def pose_callback(self, msg):
        quaternion = msg.pose.orientation
        euler = tf.transformations.euler_from_quaternion([quaternion.x, quaternion.y, quaternion.z, quaternion.w])
        self.home_orientation = euler[2]

    def yolo_result_callback(self, msg):
        rospy.loginfo("Received YOLO result message")
        rospy.loginfo("Number of detections: {}".format(len(msg.detections.detections)))
        
        track_bbox = None
        for detection in msg.detections.detections:
            track_bbox = detection.bbox
            break  
        
        if track_bbox is None:
            rospy.loginfo("Track not found. Publishing zero velocity.")
            self.publish_zero_velocity()
            return
        
        track_center_x = track_bbox.center.x
        current_orientation = self.home_orientation  
        self.follow_track(track_center_x, current_orientation)

    def follow_track(self, track_center_x, current_orientation):
        orientation_error = current_orientation - self.home_orientation
        
        if orientation_error > np.pi:
            orientation_error -= 2 * np.pi
        elif orientation_error < -np.pi:
            orientation_error += 2 * np.pi

        pid_output = self.Kp * (track_center_x - (self.image_width / 2)) + self.Ki * self.integral + self.Kd * (orientation_error - self.prev_error)
        
        self.prev_error = orientation_error
        self.integral += orientation_error

        pid_output = np.clip(pid_output, -1, 1)

        cmd_vel = Twist()
        cmd_vel.linear.x = 1.0
        cmd_vel.angular.z = pid_output

        self.cmd_vel_pub.publish(cmd_vel)

    def publish_zero_velocity(self):
        cmd_vel = Twist()
        cmd_vel.linear.x = 0.0
        cmd_vel.angular.z = 0.0
        self.cmd_vel_pub.publish(cmd_vel)

if __name__ == '__main__':
    try:
        ai_control_node = AIControlNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass