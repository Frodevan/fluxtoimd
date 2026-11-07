fluxtoimd.py is a Python 3 program to read floppy disk flux transitions
images, demodulate the data, and write the data to an ImageDisk image file.
DiscFerret (.dfi) images and ZIP files of KryoFlux Stream File images are
supported as input.

Copyright © 2016 Eric Smith <spacewar@gmail.com>

    This program is free software: you can redistribute it and/or
    modify it under the terms of version 3 of the GNU General Public
    License as published by the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see
    <http://www.gnu.org/licenses/>.

Currently fluxtoimd.py supports floppy disks in the following formats:

* IBM 3740 FM single-density
  (industry-standard single density as used by most floppy controllers)

* IBM System/34 MFM double-density
  (industry standard double-density as used by most floppy controllers)

* Alternate IBM System/34 MFM double-density with FM on the first track
  (used by both Mycron and Tandberg Data)

* Intel M2FM double-density 128 byte/sector format
  (used by SBC 202 floppy controller in Intel MDS 800/Series II/Series III
  development systems)

* HP M2FM double-density 256 byte/sector format
  (used by HP 7902, 9885, 9895)

* Metropolis GCR double-density, 128 bytes/sector, 310kbps format
  (used by for instance GenRad RDOS-II)

* Zilog hard-sectored MFM 136 bytes/sector format
  (used on the Zilog MCZ-1)

MFM format also works with most standard 5.25" and 3.5" floppy disks.
Just remember that these typically use half the bit-rate of 8" media at the same density, so double-density is 250kbps and only the high-density formats are 500kbps.
For most 8" floppy disk formats, in comparison, single-density is 250kbps and double-density is 500kbps.

USAGE:

To use with kryoflux to read Intel m2fm and fm disks (MDS/ISIS)

Read 8" single sided disk as stream file. Use -g2 to read double sided disks.
This reads each track about five times to allow error recovery.
  ./dtc  -fdirname/track -g0 -i0 -d0 -p -e76 -dd0

Zip up the output directory
  zip -rj filename.zip dirname/*

Process the files
  ./fluxtoimd -F ksf --intelm2fm filename.zip filename.imd -C "Description of disk"

Uncorrectable read errors will generate this message if all reads of sector
had data CRC error
*** BAD: track 21 sector 46

If the sector was not found or had header CRC error for all reads this error
will be generated.
*** BAD nodata: track 03 sector 26

Summary of errors are printed at the end of the conversion.

To extract the files with isisutils into a directory
  ./isis.py -x -d output_dir file.imd 

To extract into a zip file 
  ./isis.py -x -z output.zip file.imd 

To view directory
  ./isis.py -v file.imd 

For CP/M disks cpmtools can extract with this diskdef for double density
disks.
<pre>
# Intel MDS/22 8" Double Density
diskdef mds-dd
  seclen 128
  tracks 77
  sectrk 52
  blocksize 2048
  maxdir 128
  skew 0
  boottrk 2
  os 2.2
end

Untested single density
# Intel MDS/22 8" Single Density
diskdef mds-sd
  seclen 128
  tracks 77
  sectrk 26
  blocksize 1024
  maxdir 64
  skew 0
  boottrk 2
  os 2.2
end
</pre>

For cpmtools the .imd files need to be converted to raw .img file, or alternaively just use the .img extension when specifying the output filename in the fluxtoimd arguments.
Libdsk can convert
  ./libdsk-1.5.12/tools/dskconv -otype raw filename.imd filename.img
And disk utilities
  ./Disk-Utilities/disk-analyse/disk-analyse filename.imd filename.img

For directory 
  ./cpmtools/cpmls -f mds-dd filename.img

To extract
  ./cpmcp -f mds-dd filename.img '0:*' output-directory


DATA RECOVERY:

There are some features for more advanced troubleshooting, for users familiar with the encoding scheme of floppy-disks, and these are activated by setting some flags within the fluxtoimd.py file itself.
The goal of these is to dump more data to console, and let the user analyze the data on their own in order for them to do corrections to a previously extracted sector-image.
When these features are active, the amount of printout will be quite a lot. It is as such a good idea to pipe the output to a textfile for later examination, rather than to try to follow along in realtime.
To limit the amount of data to sift through, it is also possible to hardcode a list of track numbers to dump by using the "tracks" variable.

Normally, ID fields without a matching data field will always be dumped to the console, regardless of debug mode.
Data fields with incorrect checksum will be dumped only if the regular "verbosity" command-line argument is used.
This option will also add more printouts, in particular general information about the data that would typically be redundant for the ordinary user.

The "debug_dump" flag will print timing-information about address-mark placement. This can be of interest for non-standard formats, or to check if an expected data-field has been found anywhere near where it is expected.

In the case of bad or malformed data, the "log_full_dump" flag can be of interest. This will log a decoded data dump of the per-track bitstream, at all of the 16 bitshift possibilities.
This is very usefull if bits are missing, since in some cases good data will often continue with another bitshift-offset after the bad bits.
When this type of analysis is done, it is recommended that the user is familiar with testing and validating the CRC of reconstructed data-fields,
as well as knowing to what extent such reconstruction is possible based on the data that is available. Other things this data can be used for, is to identify copy-protection schemes.

In the case the data does not decode right, either due to the wrong encoding and/or bitrate being selected, setting "log_full_raw_dump" will print the bitstream of each track as-is.
Given the bitrate is right, the data-stream can be used to identify the encoding scheme, as well as the pattern of the address marks.
Such data can also provide information about missing clock-bits of other scenarios (for instance in bad sectors), or weak bits (given the flux-image contains multiple rotations per track).
The main intent of this data is however to make it easier to add support for new encoding-formats to fluxtoimg.
