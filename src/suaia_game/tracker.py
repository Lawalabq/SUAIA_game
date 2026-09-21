import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import threading
import queue


MARGIN = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54) # vibrant green

class Tracker:
    def __init__(self,shared_buffer):
            self.thread = threading.Thread(target=self.capture_hand_motion)
            self.mp_hands = mp.tasks.vision.HandLandmarksConnections
            self.mp_drawing = mp.tasks.vision.drawing_utils
            self.mp_drawing_styles = mp.tasks.vision.drawing_styles
            self.shared_buffer =shared_buffer

    def draw_landmarks_on_image(self,rgb_image, detection_result):
      

      hand_landmarks_list = detection_result.hand_landmarks
      handedness_list = detection_result.handedness
      annotated_image = np.copy(rgb_image)

      # Loop through the detected hands to visualize.
      for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        handedness = handedness_list[idx]

        # Draw the hand landmarks.
        self.mp_drawing.draw_landmarks(
          annotated_image,
          hand_landmarks,
          self.mp_hands.HAND_CONNECTIONS,
          self.mp_drawing_styles.get_default_hand_landmarks_style(),
          self.mp_drawing_styles.get_default_hand_connections_style())

        # Get the top left corner of the detected hand's bounding box.
        height, width, _ = annotated_image.shape
        x_coordinates = [landmark.x for landmark in hand_landmarks]
        y_coordinates = [landmark.y for landmark in hand_landmarks]
        text_x = int(min(x_coordinates) * width)
        text_y = int(min(y_coordinates) * height) - MARGIN

        # Draw handedness (left or left hand) on the image.
        cv2.putText(annotated_image, f"{handedness[0].category_name}",
                    (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
                    FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

      return annotated_image


    def handle_paddle_movement(self,LEFT_PLAYER_AVG_Y_CORD,RIGHT_PLAYER_AVG_CORD):
        self.shared_buffer.put([LEFT_PLAYER_AVG_Y_CORD,RIGHT_PLAYER_AVG_CORD])

    def start(self):
        self.thread.start()


    def get_avg_hand_cord(self,hand_landmarks,annotated_image):
        MIDDLE_FINGER_MCP_9 = hand_landmarks[0][8] if hand_landmarks else None
        MIDDLE_FINGER_PIP_10 = hand_landmarks[0][9] if hand_landmarks else None
        RING_FINGER_MCP_13 = hand_landmarks[0][12] if hand_landmarks else None
        RING_FINGER_PIP_14 =  hand_landmarks[0][13] if hand_landmarks else None
        
        if MIDDLE_FINGER_MCP_9 and MIDDLE_FINGER_PIP_10 and RING_FINGER_MCP_13 and RING_FINGER_PIP_14:
                        HAND_AVG_X_CORD = np.mean([MIDDLE_FINGER_MCP_9.x, MIDDLE_FINGER_PIP_10.x, RING_FINGER_MCP_13.x, RING_FINGER_PIP_14.x])
                        HAND_AVG_Y_CORD = np.mean([MIDDLE_FINGER_MCP_9.y, MIDDLE_FINGER_PIP_10.y, RING_FINGER_MCP_13.y, RING_FINGER_PIP_14.y])
        
                        # Display the angle on the image
                        cv2.putText(annotated_image, f"Hand Avg X: {HAND_AVG_X_CORD:.2f}, Hand Avg Y: {HAND_AVG_Y_CORD:.2f}",
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        return [HAND_AVG_X_CORD,HAND_AVG_Y_CORD]

        else:
             return [0.5,0.5]

        
        
        

    def capture_hand_motion(self):

            HandLandmarker = mp.tasks.vision.HandLandmarker
            VisionRunningMode = mp.tasks.vision.RunningMode

            # Setup
            base_options = python.BaseOptions(
                model_asset_path=
                'C:\\Users\\alqud\\Desktop\\2026\\SUAIA_game\\src\\suaia_game\\hand_landmarker.task'
            )

            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                running_mode=VisionRunningMode.VIDEO,
                min_hand_detection_confidence=0.3,
                min_hand_presence_confidence=0.3
            )

            # Video
            cap = cv2.VideoCapture(0)
            cap.set(3, 1200)
            cap.set(4, 1000)

            fps = cap.get(cv2.CAP_PROP_FPS)

            if fps <= 0:
                fps = 30

            frame_number = 0

            with HandLandmarker.create_from_options(options) as landmarker:

                while True:

                    # --------------------------------
                    # 1. Get full frame
                    # --------------------------------

                    ret, frame = cap.read()

                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)

                    # --------------------------------
                    # 2. Timestamp
                    # --------------------------------

                    frame_timestamp_ms = int(
                        (frame_number / fps) * 1000
                    )

                    frame_number += 1

                    # --------------------------------
                    # 3. Convert BGR -> RGB
                    # --------------------------------

                    frame_rgb = cv2.cvtColor(
                        frame,
                        cv2.COLOR_BGR2RGB
                    )

                    # --------------------------------
                    # 4. Create MediaPipe image
                    # --------------------------------

                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=frame_rgb
                    )

                    # --------------------------------
                    # 5. Detect hands on FULL FRAME
                    # --------------------------------

                    detection_result = landmarker.detect_for_video(
                        mp_image,
                        frame_timestamp_ms
                    )

                    # --------------------------------
                    # 6. Draw landmarks
                    # --------------------------------

                    annotated_frame = self.draw_landmarks_on_image(
                        frame,
                        detection_result
                    )

                    # --------------------------------
                    # 7. Split frame into left/right
                    # --------------------------------

                    frame_width = frame.shape[1]
                    frame_height = frame.shape[0]

                    middle = frame_width // 2

                    left_frame = frame[:, :middle]
                    right_frame = frame[:, middle:]

                    # --------------------------------
                    # 8. Get hand positions
                    # --------------------------------

                    left_hand_y = 0.5
                    right_hand_y = 0.5

                    if detection_result.hand_landmarks:

                        for hand_landmarks in detection_result.hand_landmarks:

                            # Get average position
                            avg_x = np.mean([
                                hand_landmarks[9].x,
                                hand_landmarks[10].x,
                                hand_landmarks[13].x,
                                hand_landmarks[14].x
                            ])

                            avg_y = np.mean([
                                hand_landmarks[9].y,
                                hand_landmarks[10].y,
                                hand_landmarks[13].y,
                                hand_landmarks[14].y
                            ])

                            # --------------------------------
                            # 9. Determine which side
                            # --------------------------------

                            if avg_x < 0.5:

                                left_hand_y = avg_y

                            else:

                                right_hand_y = avg_y

                    # --------------------------------
                    # 10. Send positions to game
                    # --------------------------------

                    self.handle_paddle_movement(
                        left_hand_y,
                        right_hand_y
                    )

                    # --------------------------------
                    # 11. Display
                    # --------------------------------

                    cv2.line(
                        annotated_frame,
                        (middle, 0),
                        (middle, frame_height),
                        (255, 255, 255),
                        2
                    )

                    cv2.imshow(
                        'Hand Tracking',
                        annotated_frame
                    )

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                cap.release()
                cv2.destroyAllWindows()

if __name__ =="__main__":
    shared_buffer = queue.Queue()

    # game = play_game(shared_buffer=shared_buffer)

    tracker = Tracker(shared_buffer=shared_buffer)
    for i in range(100):
         print(shared_buffer.get())

    tracker.start()

