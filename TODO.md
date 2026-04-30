# Video Resizer

I have a directory of videos (in nested directories) that I want to reduce in size. I want to resize them to a specific resolution (e.g., 1280x720) while maintaining the aspect ratio. I also want to ensure that the output videos are in a format that is widely supported (e.g., MP4).

I don't just want to resize them, but also ensure that output videos are shorter in size.

I want to be able to run a dry run with estimation per file (and overall) of the output size before actually processing the videos.

## Steps to Implement

1. **Identify Video Files**: Write a script to traverse the directory and identify all video files (e.g., .mp4, .avi, .mkv).
2. **Calculate New Resolution**: For each video, calculate the new resolution while maintaining the aspect ratio. This can be done by comparing the original dimensions with the target dimensions (1280x720) and scaling accordingly.
3. **Estimate Output Size**: Implement a function to estimate the output file size based on the new resolution and the original file size. This can be done using a simple ratio of the new resolution to the original resolution.
4. **Dry Run**: Create a dry run mode that outputs the estimated new resolution and file size for each video, as well as the total estimated size for all videos.
5. **Resize Videos**: Implement the actual resizing of videos using a library like FFmpeg. This will involve calling FFmpeg with the appropriate parameters to resize the video while maintaining the aspect ratio.
6. **Output Format**: Ensure that the output videos are saved in MP4 format, regardless of the original format.
7. **Error Handling**: Implement error handling to manage cases where a video cannot be processed (e.g., unsupported format, corrupted file).
8. **Logging**: Add logging to keep track of processed files, estimated sizes, and any errors encountered during processing.
9. **Command Line Interface**: Create a command line interface (CLI) to allow users to specify the input directory, target resolution, and whether to perform a dry run or actual resizing.
10. **Testing**: Test the script with a variety of video files to ensure it works correctly and efficiently.
11. Finally, also create a user interface.

## Tools and Libraries
- **FFmpeg**: A powerful multimedia framework that can be used to resize videos.
- **Python**: For scripting the video processing and handling file operations.
- **os** and **glob**: For traversing directories and identifying video files.
- **argparse**: For creating a command line interface.
- **logging**: For logging the processing steps and any errors encountered.
- **tkinter** or **PyQt**: For creating a user interface (optional).