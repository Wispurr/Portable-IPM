import argparse
from utils.vision_processing.vision_processing import RealTimeIPMProcessor

def ipm_processing():
    parser = argparse.ArgumentParser(description="IPM Processing System")
    parser.add_argument("--video", default=0, help="Video source (file path or camera index)")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--display", action="store_true", help="Display results in real-time")
    parser.add_argument("--no-perspective", action="store_true", help="Disable perspective transform")
    parser.add_argument("--no-color", action="store_true", help="Disable color detection")
    parser.add_argument("--no-lane", action="store_true", help="Disable lane detection")

    args = parser.parse_args()

    config = {
        'video_source': args.video,
        'output_file': args.output,
        'display_realtime': args.display,
        'enable_perspective_transform': not args.no_perspective,
        'enable_color_detection': not args.no_color,
        'enable_lane_detection': not args.no_lane,
    }

    processor = RealTimeIPMProcessor(config)
    processor.run()

if __name__ == "__main__":
    ipm_processing()
