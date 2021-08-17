# An interface for programs which process X-Ray diffraction images.
# This adds the code for handling the templates, directories etc.
# but not the use of them e.g. the keyworded input.
#
# This is a virtual class - and should be inherited from only for the
# purposes of using the methods.
#
# The following are considered critical to this class:
#
# Template, directory. Template in the form ### not ???
# Distance (mm), wavelength (ang), beam centre (mm, mm),
# image header information


import logging
import math
import os

from dxtbx.model.detector_helpers import set_mosflm_beam_centre
from scitbx import matrix
from xia2.Experts.FindImages import (
    digest_template,
    find_matching_images,
    image2image,
    image2template_directory,
    template_directory_number2image,
)
from xia2.Schema import load_imagesets

logger = logging.getLogger("xia2.Schema.Interfaces.FrameProcessor")


class FrameProcessor:
    """A class to handle the information needed to process X-Ray
    diffraction frames."""

    def __init__(self, image=None):
        super().__init__()

        self._fp_template = None
        self._fp_directory = None

        self._fp_matching_images = []

        self._fp_offset = 0

        self._fp_two_theta = 0.0

        self._fp_beam_prov = None

        self._fp_gain = 0.0
        self._fp_polarization = 0.0

        self._fp_header = {}

        # see FIXME for 06/SEP/06
        self._fp_xsweep = None

        # also need to keep track of allowed images in here
        self._fp_wedge = None

        self._fp_imageset = None
        # if image has been specified, construct much of this information
        # from the image

        if image:
            self._setup_from_image(image)

    def set_frame_wedge(self, start, end, apply_offset=True):
        """Set the allowed range of images for processing."""

        # XXX RJG Better to pass slice of imageset here?

        if apply_offset:
            start = start - self._fp_offset
            end = end - self._fp_offset

        self._fp_wedge = start, end

        if self._fp_matching_images:
            images = []
            for j in self._fp_matching_images:
                if j < start or j > end:
                    continue
                images.append(j)
            self._fp_matching_images = images

            ## reload the header information as well - this will be
            ## for the old wedge...# read the image header
            ## XXX this shouldn't be needed

            from dxtbx.imageset import ImageSetFactory

            imageset = ImageSetFactory.new(self.get_image_name(start))[0]

            # print this to the debug channel
            logger.debug("Latest header information for image %d:" % start)
            logger.debug(imageset.get_detector())
            logger.debug(imageset.get_scan())
            logger.debug(imageset.get_beam())
            logger.debug(imageset.get_goniometer())

            # populate wavelength, beam etc from this

            if self._fp_beam_prov is None or self._fp_beam_prov == "header":
                self._fp_beam_prov = "header"

    def get_frame_wedge(self):
        return self._fp_wedge

    def get_template(self):
        return self._fp_template

    def get_frame_offset(self):
        return self._fp_offset

    def get_directory(self):
        return self._fp_directory

    def get_matching_images(self):
        return self._fp_matching_images

    def set_wavelength(self, wavelength):
        self.get_beam_obj().set_wavelength(wavelength)

    def get_wavelength(self):
        return self.get_beam_obj().get_wavelength()

    def set_distance(self, distance):
        pass

    def get_distance(self):
        return self.get_detector()[0].get_directed_distance()

    def set_gain(self, gain):
        self._fp_gain = gain

    def get_gain(self):
        return self._fp_gain

    def set_polarization(self, polarization):
        self._fp_polarization = polarization

    def get_polarization(self):
        return self._fp_polarization

    def set_beam_centre(self, beam_centre):
        try:
            set_mosflm_beam_centre(
                self.get_detector(), self.get_beam_obj(), beam_centre
            )
            self._fp_beam_prov = "user"
        except AssertionError as e:
            logger.debug("Error setting mosflm beam centre: %s" % e)

    def get_beam_centre(self):
        detector = self.get_detector()
        beam = self.get_beam_obj()
        return get_beam_centre(detector, beam)

    def get_two_theta(self):
        return self._fp_two_theta

    def get_phi_width(self):
        return self.get_scan().get_oscillation()[1]

    def get_header(self):
        return self._fp_header

    # utility functions
    def get_image_name(self, number):
        """Convert an image number into a name."""

        return template_directory_number2image(
            self.get_template(), self.get_directory(), number
        )

    def get_image_number(self, image):
        """Convert an image name to a number."""

        if isinstance(image, type(1)):
            return image

        return image2image(image)

    # getters/setters for dxtbx objects
    def get_imageset(self):
        return self._fp_imageset

    def get_scan(self):
        return self._fp_imageset.get_scan()

    def get_detector(self):
        return self._fp_imageset.get_detector()

    def set_detector(self, detector):
        self._fp_imageset.set_detector(detector)

    def get_goniometer(self):
        return self._fp_imageset.get_goniometer()

    def set_goniometer(self, goniometer):
        self._fp_imageset.set_goniometer(goniometer)

    def get_beam_obj(self):
        return self._fp_imageset.get_beam()

    def set_beam_obj(self, beam):
        self._fp_imageset.set_beam(beam)

    def setup_from_image(self, image):
        if self._fp_template and self._fp_directory:
            raise RuntimeError("FrameProcessor implementation already set up")

        self._setup_from_image(image)

    def setup_from_imageset(self, imageset):
        if self._fp_imageset:
            raise RuntimeError("FrameProcessor implementation already set up")

        self._setup_from_imageset(imageset)

    # private methods

    def _setup_from_image(self, image):
        """Configure myself from an image name."""
        template, directory = image2template_directory(image)
        self._fp_matching_images = find_matching_images(template, directory)

        # trim this down to only allowed images...
        if self._fp_wedge:
            start, end = self._fp_wedge
            images = []
            for j in self._fp_matching_images:
                if j < start or j > end:
                    continue
                images.append(j)
            self._fp_matching_images = images

        imagesets = load_imagesets(
            template,
            directory,
            image_range=(self._fp_matching_images[0], self._fp_matching_images[-1]),
        )
        assert len(imagesets) == 1, "multiple imagesets match %s" % template
        imageset = imagesets[0]

        self._setup_from_imageset(imageset)

    def _setup_from_imageset(self, imageset):
        """Configure myself from an image name."""
        image_range = imageset.get_scan().get_image_range()

        self._fp_imageset = imageset
        try:
            self._fp_directory, self._fp_template = os.path.split(
                imageset.get_template()
            )
        except AttributeError:
            try:
                self._fp_directory = os.path.dirname(imageset.get_path(image_range[0]))
            except Exception:
                pass
        except Exception:
            pass

        self._fp_matching_images = tuple(range(image_range[0], image_range[1] + 1))

        if self._fp_beam_prov is None:
            beam = imageset.get_beam()
            detector = imageset.get_detector()
            y, x = get_beam_centre(detector, beam)
            self._fp_beam = y, x
            self._fp_beam_prov = "header"

        if self._fp_template is not None:
            self.digest_template()

    def digest_template(self):
        """Strip out common characters from the image list and move them
        to the template."""

        if self._fp_template.endswith(".h5"):
            # do not mess with the templates if container file
            return

        template, images, offset = digest_template(
            self._fp_template, self._fp_matching_images
        )

        self._fp_template = template
        self._fp_matching_images = images
        self._fp_offset = offset


def get_beam_centre(detector, beam):
    if len(detector) > 1:
        panel_id = detector.get_panel_intersection(beam.get_s0())
    else:
        panel_id = 0

    panel = detector[panel_id]
    s0 = matrix.col(beam.get_s0())
    f = matrix.col(panel.get_fast_axis())
    s = matrix.col(panel.get_slow_axis())
    n = matrix.col(panel.get_normal())
    o = matrix.col(panel.get_origin())
    # find axis of 2theta shift
    if abs(f.dot(s0)) > abs(s.dot(s0)):
        r = n.cross(s0)
        a = n.angle(s0)
    else:
        r = n.cross(s0)
        a = n.angle(s0)

    # if two theta small use old version of code - remembering modulo pi
    if abs(a % math.pi) < 5.0 * math.pi / 180.0:
        D = matrix.sqr(panel.get_D_matrix())
        v = D * beam.get_s0()
        x, y = v[0] / v[2], v[1] / v[2]
        return y, x

    # apply matrix
    R = r.axis_and_angle_as_r3_rotation_matrix(a)
    # compute beam centre at two-theta=0
    Ro = R * o
    b = -Ro + Ro.dot(s0) * s0
    beam_x = b.dot(R * f)
    beam_y = b.dot(R * s)
    return beam_y, beam_x
