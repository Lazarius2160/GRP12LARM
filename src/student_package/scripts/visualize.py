#!/usr/bin/env python
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np
import matplotlib.pyplot as plt
from std_msgs.msg import Float32
from std_msgs.msg import Bool
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped


class LoadFeature(object):


    def __init__(self):
        self.image_sub = rospy.Subscriber("/camera/rgb/image_raw",Image,self.camera_callback)
        self.bridge_object = CvBridge()
        self.x = 4
        #Publie dans le topic bottle la position du robot
        self.pubBottle = rospy.Publisher('bottle', PoseStamped , queue_size=10)
        #Souscrit au topic odom pour avoir la position du robot quand on a une bouteille
        self.subRobot = rospy.Subscriber('odom', Odometry, self.callback)   
        #Variable qui definit si la bouteille est trouvee ou non
        self.found = False


    def callback(self, data):

        if self.found : 
            bouteille = PoseStamped()
            bouteille.header.frame_id = 'odom'
            bouteille.pose.position.x = data.pose.pose.position.x
            bouteille.pose.position.y = data.pose.pose.position.y
            bouteille.pose.position.z = data.pose.pose.position.z
            self.pubBottle.publish(bouteille)
            self.found=False
            

    def camera_callback(self,data):

        try:
            # We select bgr8 because its the OpenCV encoding by default
            cv_image = self.bridge_object.imgmsg_to_cv2(data, desired_encoding="bgr8")
        except CvBridgeError as e:
            print(e)

        image_2 = cv_image
        image_1 = cv2.imread('/home/user/catkin_ws/src/student_package/scripts/coke_can6.png')
        
        gray_1 = cv2.cvtColor(image_1, cv2.COLOR_BGR2GRAY)
        gray_2 = cv2.cvtColor(image_2, cv2.COLOR_BGR2GRAY)

        #Initialize the ORB Feature detector 
        orb = cv2.ORB_create(nfeatures = 1000) 

        #Make a copy of th eoriginal image to display the keypoints found by ORB
        #This is just a representative
        preview_1 = np.copy(image_1)
        preview_2 = np.copy(image_2)

        #Create another copy to display points only
        dots = np.copy(image_1)

        #Extract the keypoints from both images
        train_keypoints, train_descriptor = orb.detectAndCompute(gray_1, None)
        test_keypoints, test_descriptor = orb.detectAndCompute(gray_2, None)

        #Draw the found Keypoints of the main image
        cv2.drawKeypoints(image_1, train_keypoints, preview_1, flags = cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        cv2.drawKeypoints(image_1, train_keypoints, dots, flags=2)

        #############################################
        ################## MATCHER ##################
        #############################################

        #Initialize the BruteForce Matcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck = True)

        #Match the feature points from both images
        matches = bf.match(train_descriptor, test_descriptor)

        #The matches with shorter distance are the ones we want.
        matches = sorted(matches, key = lambda x : x.distance)
        
        #Catch some of the matching points to draw
        good_matches = matches[:500] # THIS VALUE IS CHANGED YOU WILL SEE LATER WHY , avant 300
        
        #Parse the feature points
        train_points = np.float32([train_keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
        test_points = np.float32([test_keypoints[m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)

        #Create a mask to catch the matching points 
        #With the homography we are trying to find perspectives between two planes
        #Using the Non-deterministic RANSAC method
        M, mask = cv2.findHomography(train_points, test_points, cv2.RANSAC,5.0)
        if M is not None:

            #Catch the width and height from the main image
            h,w = gray_1.shape[:2]

            #Create a floating matrix for the new perspective
            pts = np.float32([[0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)

            #Create the perspective in the result 
            dst = cv2.perspectiveTransform(pts,M)

            # Draw the points of the new perspective in the result image (This is considered the bounding box)
            result = cv2.polylines(image_2, [np.int32(dst)], True, (50,0,255),3, cv2.LINE_AA)    

            self.found = True

        cv2.imshow('Points',preview_1)
        cv2.imshow('Detection',image_2)       
        cv2.waitKey(1)
 

    
def main():

    rospy.init_node('load_feature_node', anonymous=True) 
    load_feature_object = LoadFeature()
    rate = rospy.Rate(10) # 10hz
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("Shutting down")
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
