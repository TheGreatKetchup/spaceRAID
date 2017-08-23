#!/usr/bin/env python
"""
A piece of python code to test the effectiveness of "extract_text.py"
to better decode the video.

This loads images that have previously been chopped from the video.
It also uses a list of text with the text in the images manual transcribed by
me.
"""
import re
import os
import sys
import time
import math
import difflib
import logging

# And the local ones.
import video_loader
import process_frames

# For the talking to screen
try:
    from dummy_easygui import tkinter_check
except ImportError:
    # No dummy_easygui, just assume easygui works.
    import easygui
else:
    if tkinter_check():
        # Yes, we can use easygui.
        import easygui
    else:
        # Use Dummy Command Line Package.
        import dummy_easygui as easygui
    del tkinter_check # Clean-Up

__author__ = "Matthew Schweiss"
__version__ = "0.5"

__all__ = ["VERBOSE", "TRANSCRIPT_FILE", "main"]

VERBOSE = 4 # EDIT HOW MUCH IS PRINTED

# input for python 2.X and 3.X
try:
    raw_input
except NameError:
    raw_input = input

# For more consice repr
from repr import repr

LOGGING_LEVEL = None
VIDEO_WINDOW = None

# Make absolute paths.
try:
    __file__
except NameError:
    print_("Finding file location.")
    import inspect
    __file__ = os.path.abspath(
        inspect.getframeinfo(inspect.currentframe()).filename)
    del inspect # Don't pollute namespace.

def average(numbers):
    """Find the average of all of the numbers."""
    return float(sum(numbers)) / len(numbers) # Average

def similar(a, b):
    """Evaluate the similarity of two strings."""
    # This is built into python. Python is Great!!!
    return difflib.SequenceMatcher(None, a, b).ratio()

class Image_Transcript():
    """Read the transcript of what happened in the video."""
    def __init__(self, image_dir, image_format, transcript_file):
        """Create a transcript."""
        # make the file and directory absolute.
        self.source = open(transcript_file)
        self.last_frame = None
        self.next_frame = None

        self.image_dir    = os.path.normpath(image_dir)
        print("Image Directory: %s" % image_dir)
        self.image_format = image_format

    def _parse(self, line):
        """Parse the line into a readable form."""
        logging.info("Read line %r." % line)
        line = line.strip()
        if not line or line[:1] == '#': # Comment, ignore line.
            return None
        content = list(re.split("\\t", line, 3))
        while len(content) < 3:content.append("")
        frame_number, name_result, time_result = content[:3]
        # frame_number is a string, try to parse.
        if not frame_number.isdigit():
            frame_number = os.path.basename(frame_number)
            if frame_number.startswith("image"):
                # File is image\d+\.(?:jpg|png)
                ext_start = frame_number.rfind(".")
                if ext_start:
                    frame_number = frame_number[5:ext_start]
                else:
                    frame_number = frame_number[5:]

        if frame_number.isdigit():
            frame_number = int(frame_number)
        else:
            logging.warning(
                "Could not read the frame_number %r from transcript %r." \
                % (content[0], self.source.name))
            frame_number = self.last_frame[0] + 1 if self.last_frame else 1

        # Now, take the frame_number and actually load the frame.
        file_path = os.path.join(self.image_dir, self.image_format % frame_number)
        frame = video_loader.load_image(file_path)
        # Finished processing, now do something with it.
        return frame_number, frame, name_result, time_result

    def next(self):
        """Return the next frame."""
        rerun = True
        while rerun: # Recursion is needed at least once, maybe more.
            # Stop rerun
            rerun = False

            if self.closed:
                raise StopIteration()
            # If we have a next_frame we are working toward, do that.
            if self.next_frame is not None and self.last_frame is not None:
                if self.last_frame[0] + 1 < self.next_frame[0]:
                    # Next frame is NOT immediately after next frame.
                    # Return the last frame again.
                    self.last_frame[0] += 1
                    return self.last_frame[1:] # Don't return frame_number
                elif self.last_frame[0] + 1 >= self.next_frame[0]:
                    # We have gone through all of the required frames.
                    # Finish this iteration.
                    self.last_frame = self.next_frame
                    self.next_frame = None
                    return self.last_frame[1:] # Don't return frame_number

            # Otherwise, load another frame.
            else:
                for line in self.source:
                    # Send the new line to be parsed.
                    line = self._parse(line)
                    if line is None:
                        continue
                    frame_number, frame, name_result, time_result = line

                    if self.last_frame is None or \
                       frame_number == self.last_frame[0] + 1:
                        # This is the next frame, go ahead and return it.
                        self.last_frame=(frame_number,frame,name_result,time_result)

                        self.next_frame = None
                        return self.last_frame[1:] # Don't return frame_number.
                    else:
                        # This frame is actually for a frame that has not happened yet.
                        # The current frame is actually the same as the last frame.
                        #self.last_frame = self.next_frame
                        self.next_frame=(frame_number,frame,name_result,time_result)

                        # Rerun to return first frame.
                        rerun = True
                        break
                else:
                    # Finished file. We are done here.
                    self.close()

    __next__ = next

    def __iter__(self):
        """Move through the next frame."""
        while True:
            r = self.next()
            if r is None:
                logging.debug("Image Transcript Read EOF.")
                raise StopIteration()

            else:
                yield r

    @property
    def closed(self):
        """Return if the file is closed."""
        return self.source.closed

    def close(self):
        if not self.closed:
            self.source.close()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

def test(src, VIDEO_WINDOW = VIDEO_WINDOW, LOGGING_LEVEL = LOGGING_LEVEL):
    """Test the process frames."""
    # First, some options to the test to run.
    global read_name_results, read_time_results
    # Just to get everything on one line, here are some convinent functions.
    read_name_results = []
    read_time_results = []

    exc_time_results  = []

    if not VERBOSE:
        print("Frame")
    if process_frames.ADAPTIVE_CLASSIFIER:
        print("ADAPTIVE_CLASSIFIER: Enabled")
    else:
        print("ADAPTIVE_CLASSIFIER: Disabled")
    if process_frames.ALLOW_FAILURE:
        print("ALLOW_FAILURE: Enabled")
    else:
        print("ALLOW_FAILURE: Disabled")
    print("VERBOSE: %d" % VERBOSE)
    print("VIDEO_WINDOW: %r" % VIDEO_WINDOW)
    print("LOGGING_LEVEL: %r" % logging.getLevelName(LOGGING_LEVEL))
    print("Working File: %r" % __file__)

    # Initalize the process_frames.
    print("Initalizing process_frames.")
    process_frames.init()

    # Give pooling information.
    print("Using %d name generators." % process_frames.NAME_POOL.qsize())
    print("Using %d time generators." % process_frames.TIME_POOL.qsize())

    failed_frames = 0
    exc_start_time = time.time()

    try:
        for img_num, k in enumerate(src):
            if isinstance(k, (tuple, list)):
                frame, real_name, real_time = k
            else:
                frame, real_name, real_time = k, None, None

            frame_time_start = time.time() # Timing

            # Video Window
            if VIDEO_WINDOW:
                video_loader.show_image(frame)

            # Back to analysis
            if frame is None:
                logging.error("Frame failed to read.")
                continue
            read_name, read_time = process_frames.read_image(frame)

            frame_time_stop = time.time() # Timing
            frame_time = frame_time_stop - frame_time_start
            # Now use all of those breakdowns to come up with one super selection.
            if VERBOSE == 5:
                print("F %d\tActual\tRead" % img_num)
                print("Name:\t%r\t%r" % (real_name, read_name))
                print("Time:\t%r\t%r" % (real_time, read_time))
            elif VERBOSE == 4:
                print("F %d\tName A:%s\tR:%r\tTime A:%s\tR:%s" %
                      (img_num, real_name, read_name, real_time,
                       repr(read_time) if read_time is not None else read_time))
            elif VERBOSE == 3:
                print("F %d\t%r\t%r" % (img_num, read_nume, read_time))
            elif VERBOSE == 2:
                print("Processing frame %d in %.3f seconds." %
                      (img_num, frame_time))
            elif VERBOSE == 1:
                # Print 1,2,3,4,5,6...9,10,20,30,40,...,100,200,300...
                # If this is a multiple of 10, 100, or 1000 correspondingly.
                # log10(0) will crash so 0 is allowed expicitly.
                if img_num == 0 or img_num % (10 ** math.floor(math.log10(img_num))) == 0:
                    print("Processed up to frame %d in %.3f seconds." %
                          (img_num, time.time() - exc_start_time))
            else:
                # Don't Print Anything.
                pass
            # real_name or real_time could be None if the read failed.
            # In this case. If it is None, do similar as if it were "".
            if real_name is not None:
                read_name_results.append(
                    (read_name,
                     similar(real_name, read_name or ""),
                     read_name == real_name))
            else:
                read_name_results.append(
                    (read_name,
                     None,
                     None))

            if real_time is not None:
                read_time_results.append(
                    (read_time,
                     similar(real_time, read_time or ""),
                     read_time == real_time))
            else:
                read_time_results.append(
                    (read_time,
                     None,
                     None))

            if read_name is None or read_time is None:
                failed_frames += 1
            exc_time_results.append(frame_time)

    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        exc_stop_time = time.time()

        exc_time = exc_stop_time - exc_start_time
        print("")
        # Now that we are done, print summary information.

        # Make sure img_num exists.
        try:
            img_num
        except NameError:
            img_num = 0

        print("%s Frames\tPartial Matches\tPerfect Matches" % img_num)

        not_none = lambda x: x is not None
        # Print Name    
        try:
            name_partial_percent = average(
                filter(not_none, zip(*read_name_results)[1])) * 100
            name_perfect_percent = average(
                filter(not_none, zip(*read_name_results)[2])) * 100
            print("Name\t\t%6.2f%%\t%6.2f%%" %
                  (name_partial_percent, name_perfect_percent))
        except (IndexError,         # Caused by no results
                ZeroDivisionError   # Caused by "None" results.
                ):
            print("Name\t\tN/A\t\tN/A")
        try:
            time_partial_percent = average(
                filter(not_none, zip(*read_time_results)[1])) * 100
            time_perfect_percent = average(
                filter(not_none, zip(*read_time_results)[2])) * 100
            print("Time\t\t%6.2f%%\t%6.2f%%" %
                  (time_partial_percent, time_perfect_percent))
        except (IndexError,         # Caused by no results
                ZeroDivisionError   # Caused by "None" results.
                ):
            print("Time\t\tN/A\t\tN/A")
        print("Processed Frames: %d" % len(exc_time_results))
        print("Failed Frames: %d" % failed_frames)
        if exc_time_results:
            print(" Average Time:\t%.3f seconds" % average(exc_time_results))
        else:
            print(" Average Time:\tN/A seconds")
        print("   Total Time:\t%.3f seconds" % exc_time)

def main(args = None, VIDEO_WINDOW=VIDEO_WINDOW,LOGGING_LEVEL=LOGGING_LEVEL):
    # Get test Information
    test_num = easygui.indexbox(
        msg="Hello! What do you want to test?",
        choices=("process_frames.read_frame()", "find_matches.read_moment()")
        )

    if   test_num == 0:
        test_func = process_frames.read_image

    elif test_num == 1:
        test_func = find_matches.read_moment

    if test_num is None:
        # Exit
        return

    # Get VIDEO_WINDOW if needed.
    if VIDEO_WINDOW is None:
        VIDEO_WINDOW = easygui.ynbox("Do you want to display the video feed?")

        if VIDEO_WINDOW is None:
            # Exit
            return

    # Get LOGGING_LEVEL if needed.
    if LOGGING_LEVEL is None:
        LOGGING_LEVEL = easygui.indexbox(
            msg="What amount of debug information do you want to see?",
            choices=("DEBUG and more severe (Most Output).",
                     "INFO and more severe.",
                     "WARNING and more severe.",
                     "ERROR and more severe.",
                     "CRITICAL and more severe.",
                     "FATAL (Least Output).")
            )
       
        if   LOGGING_LEVEL == 0: LOGGING_LEVEL = logging.DEBUG
        elif LOGGING_LEVEL == 1: LOGGING_LEVEL = logging.INFO
        elif LOGGING_LEVEL == 2: LOGGING_LEVEL = logging.WARNING
        elif LOGGING_LEVEL == 3: LOGGING_LEVEL = logging.ERROR
        elif LOGGING_LEVEL == 4: LOGGING_LEVEL = logging.CRITICAL
        elif LOGGING_LEVEL == 5: LOGGING_LEVEL = logging.FATAL

    # Allow for more logging information.
    logging.getLogger().setLevel(LOGGING_LEVEL)

    if test_num == 0:
        # process_frames.read_frame() test.
        # images or video.
        test_set = easygui.indexbox(
            msg = "What test set do you want to use?",
            choices = ('Video "Qualification Match 5.mov" with 7995 frames.',
                       'Video "Saturday 3-11-17_ND.mp4" with 1,194,263 frames.',
                       'Set of 7995 png images.',
                       'Set of 56 jpg images.')
            )
    else:
        # find_matches.read_moment()
        # video only.
        test_set = easygui.indexbox(
            msg = "What test set do you want to use?",
            choices = ('Video "Qualification Match 5.mov" with 7995 frames.',
                       'Video "Saturday 3-11-17_ND.mp4" with 1,194,263 frames.',
                       )
            )

    if test_set is None:
        # Exit
        return

    basename = os.path.dirname(os.path.abspath(__file__))

    if   test_set == 0:
        # Qualification Video.
        src = video_loader.Video(
            os.path.join(basename, "./Examples/Qualification Match 5.mov"))

    elif test_set == 1:
        # Saturday huge video.
        src = video_loader.Video(
            os.path.join(basename, "./Examples/Saturday 3-11-17_ND.mp4"))

    elif test_set == 2:
        # "All" Set.
        src = Image_Transcript(
                os.path.join(basename, "./Examples/All"),
                "image%d.png",
                os.path.join(basename, "./Examples/All/textInImages.txt")
                )

    elif test_set == 3:
        # "Every5" Set.
        src = Image_Transcript(
                os.path.join(basename, "./Examples/Every5Sec"),
                "image%d.jpg",
                os.path.join(basename, "./Examples/Every5Sec/textInImages.txt")
                )

    else:
        # Error? How did we get here.
        raise RuntimeError("Could not process the test set %r. Bad number." % test_set)

    # So, now we have src.
    # Run it!
    test(src, VIDEO_WINDOW, LOGGING_LEVEL)

if __name__ == '__main__':
    main()