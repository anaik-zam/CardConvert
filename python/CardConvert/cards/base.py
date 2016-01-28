import os
import re
import copy
import shutil
import inspect
import logging
import subprocess
from CardConvert import exceptions

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class BasicCard(object):
    """ This is the base class of a card class. It has functions to generate various formats of the card. eg animated gifs,
    mp4, webm, jpg, resized pngs, icons of various sizes. It also has convenience functions to generate a dict of all
    the cards of it's class residing in a given folder. It can generate instances for each of the cards in the dict.
    This class is subclassed by the card classes to implement their conversion functions.
    """
    def __init__(self, config, name='', locale='', info=None):
        """
        Constructor
        Args:
            config (dict): configuration (CardConvert.yaml in the config folder)
            name (str): name of this card
            locale (str): locale this card belongs to (eg: enUs, esES)
            info (dict): dict containing info about all the files pertaining to this card
                         eg {'static': 'path to static file',
                             'animated': [all frames]}
        """
        self._config = config
        self._info = info or {}
        self.name = name
        self.locale = locale

    def __repr__(self):
        """
        Prints Cards Name: Locale : Static file path
        Returns:
             str
        """
        file_ = self._info.get('static', '')
        return '%s:%s::%s' % (self.name, self.locale, file_)

    @property
    def card_class(self):
        """
        Property that holds class of the card eg: output, heroes, cardbacks.
        Returns:
             str
        """
        raise NotImplementedError

    @property
    def config(self):
        """
        Property that holds config info.
        Returns:
             dict
        """
        return self._config

    @staticmethod
    def crawler(target_dir, frame_re, anim_folder, locale_list=None):
        """
        Function to os.walk through a target directory and collect all the cards in it.
        Args:
            target_dir (str): path to crawl
            frame_re (str): regex expression to delimit frame counter
            anim_folder (str): name of the subdir in the target_dir that contains the animated frames
            locale_list (list): list of supported locales
        Returns:
            cards (dict): cards in the target_dir with it's files
                          eg: {$card_name: {'static': 'file path', 'animated': [frames]}}
        """
        cards = {}
        if os.path.isdir(target_dir):
            for path, subdir, files in os.walk(target_dir):
                animated = False
                basename = os.path.basename(path)
                if basename == anim_folder:
                    animated = True
                if not animated:
                    for file_ in sorted(files):
                        if not re.match('^\.', file_):
                            fullpath = os.path.join(path, file_)
                            header = os.path.splitext(file_)[0]
                            if header not in cards:
                                cards[header] = {'static': fullpath,
                                                 'animated': []}
                if animated:
                    for file_ in sorted(files):
                        if not re.match('^\.', file_):
                            fullpath = os.path.join(path, file_)
                            header = os.path.splitext(file_)[0]
                            header = re.split(frame_re, header)[0]
                            if header in cards:
                                cards[header]['animated'].append(fullpath)

        return cards

    @staticmethod
    def run_cmd(cmd):
        """
        Function to execute a command as subprocess.
        Args:
            cmd (str): command to execute
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.debug('Executing: %s' % cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_value, stderr_value = proc.communicate()
        return_code = proc.returncode
        return return_code, stdout_value, stderr_value

    def crawl_for_this_card_class(self, target_dir):
        """
        Convenience function to crawl a target dir for this class of cards.
        Args:
            target_dir (str): path to crawl
        Returns:
            dict: cards in the target_dir with it's files
                  eg: {$card_name: {'static': 'file path', 'animated': [frames]}}
        """
        frame_re = self.config['card_types'][self.card_class]['frame_re']
        anim_folder = self.config['card_types'][self.card_class]['anim_folder']
        locale = self.config['locale']
        return self.crawler(target_dir, frame_re, anim_folder, locale_list=locale)

    def create_instances(self, cards_dict):
        """
        Convenience function to generate instances from a card_dict.
        Args:
            cards_dict (dict): dict generated by the crawler function
        Returns:
            list: list of instances of this class
        """
        raise NotImplementedError

    def _get_input_output(self, output_type):
        """
        Function to get the path of current static file (input) and generate the output path based on output type.
        This should only be called after _make_output_folders is called.
        Args:
            output_type (str): output type (valid types in CardConvert)
        Returns:
            input_ (str): path to input file
            output (str): path to output file
        """
        input_ = self._info['static']
        basename = os.path.basename(input_)
        output = self._info['output_paths'][output_type]
        output = os.path.join(output, basename)
        return input_, output

    def _make_output_folders(self, output_dir):
        """
        Function to all the output folders on disk with output_dir as the base folder.
        The function looks up the CardConvert.yaml config to determine which folders to build for this class of card.
        It also stores the output paths in self._info['output_paths']
        Args:
            output_dir (str): base output path
        """
        logger.info('CREATING OUTPUT FOLDERS:: %s:%s' % (self.name, self.locale))
        outputs = self.config['card_types'][self.card_class]['outputs']
        self._info['output_paths'] = {}
        for output in outputs:
            path = os.path.join(output_dir, self.card_class, self.locale, output)
            try:
                logger.debug('Creating folder: %s' % path)
                os.makedirs(path)
            except OSError:
                pass
            self._info['output_paths'][output] = path

    @staticmethod
    def _make_medium_copy_cmd(input_, output):
        """
        Function to build a cmd to make a medium copy of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'convert %s -filter lanczos -resize 200x303 -unsharp 1.5x1+0.7+0.02 %s' % (input_, output)

    def _make_medium_copy(self):
        """
        Function to create a medium sized copy of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING MEDIUM SIZED COPY:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('medium')
        cmd = self._make_medium_copy_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeMediumCopyError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    @staticmethod
    def _make_small_copy_cmd(input_, output):
        """
        Function to build a cmd to make a small copy of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'convert %s -filter lanczos -resize 123x186 -unsharp 1.5x1+0.7+0.02 %s' % (input_, output)

    def _make_small_copy(self):
        """
        Function to create a small sized copy of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING SMALL SIZED COPY:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('small')
        cmd = self._make_small_copy_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeSmallCopyError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    @staticmethod
    def _make_jpg_copy_cmd(input_, output):
        """
        Function to build a cmd to make a jpg copy of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'convert %s -background "#242424" -layers flatten -filter lanczos -resize 200x303 +repage -gravity south -crop 200x302+0+0 +repage -unsharp 1.5x1+0.7+0.02 -quality 85%% %s' % (input_, output)

    def _make_jpg_copy(self):
        """
        Function to create a jpg copy of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING MEDIUM SIZED JPG COPY:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('mediumj')
        output, ext = os.path.splitext(output)
        output = '%s.jpg' % output
        cmd = self._make_jpg_copy_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeJpgCopyError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    @staticmethod
    def _make_small_icons_cmd(input_, output):
        """
        Function to build a cmd to make a small icon of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'convert %s -filter lanczos -resize 11x16 -unsharp 1.5x1+0.7+0.02 %s' % (input_, output)

    def _make_small_icons(self):
        """
        Function to create a small icon of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING SMALL SIZED ICON:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('icons/small')
        cmd = self._make_small_icons_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeSmallIconError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    @staticmethod
    def _make_medium_icons_cmd(input_, output):
        """
        Function to build a cmd to make a medium icon of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'convert %s -filter lanczos -resize 30x44 -unsharp 1.5x1+0.7+0.02 %s' % (input_, output)

    def _make_medium_icons(self):
        """
        Function to create a medium icon of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING MEDIUM SIZED ICON:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('icons/medium')
        cmd = self._make_medium_icons_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeMediumIconError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    @staticmethod
    def _make_large_icons_cmd(input_, output):
        """
        Function to build a cmd to make a large icon of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'convert %s -filter lanczos -resize 40x60 -unsharp 1.5x1+0.7+0.02 %s' % (input_, output)

    def _make_large_icons(self):
        """
        Function to create a large icon of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING LARGE SIZED ICON:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('icons/large')
        cmd = self._make_large_icons_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeLargeIconError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    def _make_animated_png_cmd(self, input_, output):
        """
        Function to build a cmd to make a animated png of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            cmd (str): command to execute
        """
        cmd = 'apngasm %s ' % output
        for file_ in self._info['animated']:
            cmd += '%s ' % file_
        return cmd

    def _make_animated_png(self):
        """
        Function to create a animated png of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        if self._info['animated']:
            logger.info('CREATING ANIMATED PNG:: %s:%s' % (self.name, self.locale))
            input_, output = self._get_input_output('animated')
            cmd = self._make_animated_png_cmd(input_, output)
            return_code, stdout_value, stderr_value = self.run_cmd(cmd)
            if return_code != 0:
                raise exceptions.MakeAnimatedPNGError(cmd, return_code, stdout_value, stderr_value)
            return return_code, stdout_value, stderr_value
        else:
            print 'No animation for %s' % self.name

    @staticmethod
    def _make_animated_gif_cmd(input_, output):
        """
        Function to build a cmd to make a animated gif of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'apng2gif %s %s' % (input_, output)

    def _make_animated_gif(self):
        """
        Function to create a animated gif of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING ANIMATED GIF:: %s:%s' % (self.name, self.locale))
        input_, output = self._get_input_output('animated')
        ## the animated png created from the _maked_animated_png is out input to create the gif
        input_ = copy.copy(output)
        output, ext = os.path.splitext(output)
        output = '%s.gif' % output
        cmd = self._make_animated_gif_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeAnimatedGIFError(cmd, return_code, stdout_value, stderr_value)
        # remove the png
        logger.debug('Removing input png file: %s' % input_)
        os.remove(input_)
        return return_code, stdout_value, stderr_value

    def _web_format_prep(self, fext='mp4'):
        """
        Function to get the input and output path for generating web formats. The inputs are different for these
        as the input are the ff_ prefixed pngs in the animation_temp folder generated from _composite_animation_frames
        Args:
            fext (str): output frame extension
        Returns:
            this_input_ (str): path to input file
            output (str): path to output file
        """
        input_ = self._info['ff_out'][0]
        header, ext = os.path.splitext(input_)
        frame_re = self.config['card_types'][self.card_class]['frame_re']
        header = re.sub(frame_re, '_%04d', header)
        this_input_ = '%s%s' % (header, ext)
        input_, output = self._get_input_output('animated')
        output, ext = os.path.splitext(output)
        output = '%s.%s' % (output, fext)
        return this_input_, output

    @staticmethod
    def _make_mp4_cmd(input_, output):
        """
        Function to build a cmd to make a mp4 of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'ffmpeg -f image2 -framerate 11 -i %s -profile:v baseline -level 3.0 -pix_fmt yuv420p %s' % (input_,
                                                                                                           output)

    def _make_mp4(self):
        """
        Function to create a mp4 of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING MP4:: %s:%s' % (self.name, self.locale))
        input_, output = self._web_format_prep(fext='mp4')
        cmd = self._make_mp4_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeMP4Error(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    @staticmethod
    def _make_webm_cmd(input_, output):
        """
        Function to build a cmd to make a mp4 of this card.
        Args:
            input_ (str): input file path
            output (str): output file path
        Returns:
            str: command to execute
        """
        return 'ffmpeg -f image2 -framerate 11 -i %s  %s' % (input_, output)

    def _make_webm(self):
        """
        Function to create a webm of this card.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        logger.info('CREATING WEBM:: %s:%s' % (self.name, self.locale))
        input_, output = self._web_format_prep(fext='webm')
        cmd = self._make_webm_cmd(input_, output)
        return_code, stdout_value, stderr_value = self.run_cmd(cmd)
        if return_code != 0:
            raise exceptions.MakeWEBMError(cmd, return_code, stdout_value, stderr_value)
        return return_code, stdout_value, stderr_value

    def _get_bg_path(self):
        """
        Function to get the path to the background image to be composited for cardbacks. This looks up the config
        CardConvert.yaml
        Returns:
            bg_path (str): path to the image
        """
        bg_basename = self.config['card_types'][self.card_class]['composite']
        bg_folder = os.getenv('BACKGROUNDS_FOLDER')
        if not bg_folder:
            current_frame = inspect.currentframe()
            src_file = inspect.getsourcefile(current_frame)
            module_folder = re.split('python', src_file)[0]
            bg_folder = os.path.join(module_folder, 'backgrounds')
        bg_path = os.path.join(bg_folder, bg_basename)
        return bg_path

    def _cp_original(self, output_dir):
        """
        Function to make copies of the original card images into the output_dir
        Args:
            output_dir (str): base output path
        """
        logger.info('COPYING ORIGINALS:: %s:%s' % (self.name, self.locale))
        input_ = self._info['static']
        output = os.path.join(output_dir, self.card_class, self.locale, 'original')
        shutil.copy2(input_, output)
        logger.debug('Copied %s ---> %s' % (input_, output))

    def _make_copies(self):
        """
        Function to create copies of this card depending on the card class and it's config
        """
        raise NotImplementedError

    def _make_animation_copies(self):
        """
        Function to create animated copies of this card depending on the card class and it's config
        """
        raise NotImplementedError

    def _composite_animation_frames(self):
        """
        Function to comp the card with a bg.
        Returns:
            return_code (int): process return code
            stdout_value (str): stdout
            stderr_values (str): stderr
        """
        raise NotImplementedError

    def process(self, output_dir):
        """
        This function defines the process of how a card is processed.
        Creates output folders
        Copies original files to output folders
        Make copies of this card (small, medium, jpg etc)
        Make animated copies of this card (animated gif, png, webm, mp4)
        Args:
            output_dir (str): base output path
        """
        logger.info('PROCESSING:: %s:%s' % (self.name, self.locale))
        self._make_output_folders(output_dir)
        self._cp_original(output_dir)
        self._make_copies()
        self._make_animation_copies()

        return 'Finished processing %s:%s' % (self.name, self.locale)
