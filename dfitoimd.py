#!/usr/bin/env python3
# data extraction from floppy disk flux transition images
# Copyright 2016 Eric Smith <spacewar@gmail.com>

#    This program is free software: you can redistribute it and/or
#    modify it under the terms of version 3 of the GNU General Public
#    License as published by the Free Software Foundation.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

import argparse
import re
from collections import OrderedDict

from dfi import DFI
from adpll import ADPLL
from crc import CRC
from modulation import FM, MFM, IntelM2FM
from imagedisk import ImageDisk


def hex_dump(b, prefix = ''):
    for i in range(0, len(b), 16):
        print(prefix + '%02x: ' % i, end='')
        for j in range(16):
            if (i + j) < len(b):
                print('%02x ' % b[i+j], end='')
            else:
                print('   ', end='')
        for j in range(16):
            if (i + j) < len(b):
                if 0x20 <= b[i+j] <= 0x7e:
                    print('%c' % b[i+j], end='')
                else:
                    print('.', end='')
        print()


def dump_track(modulation, image, track,
               sectors_per_track = None,
               require_index_mark = False):

    if sectors_per_track is None:
        sectors_per_track = modulation.default_sectors_per_track

    sectors = OrderedDict()

    block = image.blocks[(track, 0, 1)]

    di = block.get_delta_iter()

    adpll = ADPLL(di,
                  osc_period = hbc,
                  max_adj_pct = 3.0,
                  window_pct = 50.0,
                  freq_adj_factor = 0.005,
                  phase_adj_factor = 0.1)


    bits = ''
    for b in adpll:
        bits += '01'[b]
    #print(len(bits))

    if require_index_mark:
        index_address_mark_locs = [m.start() for m in re.finditer(modulation.index_address_mark, bits)]
        if not index_address_mark_locs:
            print('track %d: no index address mark found' % track)
            return sectors

    id_address_mark_locs = [m.start() for m in re.finditer(modulation.id_address_mark, bits)]
    #print('id address marks at: ', id_address_mark_locs)

    for id_pos in id_address_mark_locs:
        #print('id address mark at channel bit %d' % id_pos)
        id_field = modulation.decode(bits[id_pos: id_pos + len(modulation.id_address_mark) + 96])
        crc.reset()
        crc.comp(id_field)
        if crc.get() != 0:
            print("*** bad ID field CRC %04x" % crc.get())
            hex_dump(id_field)
            continue
        id_track, id_head, id_sector, id_size = id_field[1:5]
        if id_track != track:
            print("*** ID field with wrong track number")
            hex_dump(id_field)
            continue
        if id_size != 0:
            print("*** ID field with sector size")
            hex_dump(id_field)
            continue
        if (id_sector in sectors) and (sectors[id_sector][1] is not None):
            continue  # already have this one
        sectors[id_sector] = [False, None]

        bc = 128 << id_size

        deleted = False
        data_pos = bits.find(modulation.data_address_mark, id_pos + len(modulation.id_address_mark) + 96)
        if (modulation.id_to_data_half_bits - 50) <= (data_pos - id_pos) <= (modulation.id_to_data_half_bits + 50):
            #print('  data address mark at channel bit offset %d' % (data_pos - id_pos))
            pass
        else:
            data_pos = bits.find(modulation.deleted_data_address_mark, id_pos + len(modulation.id_address_mark) + 96)
            if (modulation.id_to_data_half_bits - 50) <= (data_pos - id_pos) <= (modulation.id_to_data_half_bits + 50):
                #print('  deleted data address mark at channel bit offset %d' % (deleted_data_pos - id_pos))
                deleted = True
            else:
                print('*** ID field without data field ***')
                hex_dump(id_field)
                continue

        data_field = modulation.decode(bits[data_pos: data_pos + len(modulation.id_address_mark) + (bc + 2) * 16])
        crc.reset()
        crc.comp(data_field)
        if crc.get() != 0:
            print("*** bad data field CRC")
            continue

        sectors [id_sector] = (deleted, data_field[1:bc+1])

    return sectors


parser = argparse.ArgumentParser(description = 'DFI library test, prints flux transition time histogram for a chosen track',
                                     formatter_class = argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('dfi_image', type=argparse.FileType('rb'))
parser.add_argument('imagedisk_image', type=argparse.FileType('wb'))

parser_modulation = parser.add_mutually_exclusive_group(required = False)
parser_modulation.add_argument('--fm',   action = 'store_const', const = FM,   dest = 'modulation', help = 'FM modulation, IBM 3740 single density')
parser_modulation.add_argument('--mfm',  action = 'store_const', const = MFM,  dest = 'modulation', help = 'MFM modulation, IBM System/34 double density')
parser_modulation.add_argument('--m2fm', action = 'store_const', const = IntelM2FM, dest = 'modulation', help = 'M2FM modulation, Intel MDS, SBC 202 double density')

parser.set_defaults(modulation = 'fm')

parser.add_argument('-f', '--frequency',  type=float, help = 'sample rate in MHz', default=25.0)
parser.add_argument('-b', '--bit-rate',   type=float, help = 'bit rate in Kbps')
parser.add_argument('--index',            action = 'store_true', help = 'require tracks to have index address marks')
parser.add_argument('-v', '--verbose',    action = 'store_true')
args = parser.parse_args()

dfi_image = DFI(args.dfi_image, frequency = args.frequency * 1.0e6)

if args.imagedisk_image is not None:
    imd = ImageDisk()

if args.bit_rate is None:
    args.bit_rate = args.modulation.default_bit_rate_kbps


crc_param = CRC.CRCParam(name = 'CRC-16-CCITT',
                         order = 16,
                         poly = 0x1021,
                         init = args.modulation.crc_init,
                         xorot = 0x0000,
                         refin = False,
                         refot = False)


crc = CRC(crc_param)
crc.make_table(8)


hbr = args.bit_rate * 2000   # half-bit rate in Hz
hbc = 1/hbr                  # half-bit cycle in s


sectors_per_track = args.modulation.default_sectors_per_track

bad_sectors = 0
data_sectors = 0
deleted_sectors = 0
total_sectors = 0


tracks = [None] * 77
for track_num in range(77):
    track = dump_track(args.modulation, dfi_image, track_num, require_index_mark = args.index)
    tracks [track_num] = track
    if args.verbose:
        print('%2d: ' % track_num, end='')
    for sector_num in range(1, sectors_per_track + 1):
        total_sectors += 1
        if sector_num not in track:
            if args.verbose:
                print('*', end='')
            bad_sectors += 1
            continue
        sector = track[sector_num]
        if sector[0]:
            if args.verbose:
                print('D', end='')
            deleted_sectors += 1
        else:
            if args.verbose:
                print('.', end='')
            data_sectors += 1
    if args.verbose:
        print()

    if args.imagedisk_image is not None:
        for sector_num in track:
            deleted = track[sector_num][0]
            data = track[sector_num][1]
            if data is not None:
                #print('writing track %02d sector %02d\n' % (track_num, sector_num))
                imd.write_sector(args.modulation.imagedisk_mode,
                                 track_num,  # cylinder
                                 0,      # head
                                 sector_num,
                                 bytes(data),
                                 deleted = deleted)
            else:
                # XXX don't yet have support from imagedisk.py for bad sectors
                print('*** BAD: track %02d sector %02d\n' % (track_num, sector_num))
                pass

if args.imagedisk_image is not None:
    imd.write(args.imagedisk_image)

print('%d data sectors, %d deleted data sectors, %d bad sectors, out of %d' % (data_sectors, deleted_sectors, bad_sectors, total_sectors))

