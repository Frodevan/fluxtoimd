from adpll import ADPLL

def dump_wang_hard_sector_track(image, track):
    sectors = OrderedDict()
    for n in range(16):
        sectors[n+1] = [False, None, True]

    block = image.blocks[(track, 0, 1)]

    adpll = ADPLL(block.get_delta_iter(),
                  osc_period = hbc,
                  max_adj_pct = 3.0,
                  window_pct = 50.0,
                  freq_adj_factor = 0.005,
                  phase_adj_factor = 0.1)

    clock = False
    data = ''
    for b in adpll:
        if not clock:
            data += '01'[b]
        if b == 0 and clock:
            data += 'R'
            clock = False
        clock = not clock

    bitcount = -1
    track_nr = -1
    sector_nr = -1
    byte_nr = -1
    bit_nr = 0
    trust = False
    leading_zero_count = 0
    temp_byte = 0
    data_field = []
    for b in data:
        bitcount += 1
        if b != 'R':
            temp_byte = ((temp_byte<<1)+int(b))&255
            bit_nr = (bit_nr+1)&7
            if byte_nr == -1:
                if b == '0':
                    leading_zero_count += 1
                elif temp_byte == 3 and leading_zero_count > 100:
                    byte_nr = 0
                    bit_nr = 0
                    leading_zero_count = 0
                    trust = (sector_nr == -1) or trust
                    if sector_nr == -1:
                        print('Mark initiated on track {} bit {}: {} {} {}'.format(track, bitcount, data[bitcount-16:bitcount+1], data[bitcount+1:bitcount+9], data[bitcount+9:bitcount+17]))
                    #else:
                    #    print('\tMark initiated on track {} bit {}: {}'.format(track, bitcount, data[bitcount-16:bitcount+1]))
                elif temp_byte != 1:
                    leading_zero_count = 0
            elif bit_nr == 0:
                byte_nr += 1
        else:
            temp_byte = (temp_byte<<1)&255
            bit_nr = (bit_nr+1)&7
            #leading_zero_count = 0

        if bit_nr == 0 and byte_nr != -1:
            if sector_nr == -1:
                if byte_nr == 1:
                    track_nr = temp_byte
                elif byte_nr == 2:
                    sector_nr = temp_byte
                    data_field = []
                    byte_nr = -1
                    if sector_nr > 16:
                        print('\tInvalid header, track {} sector {} on track {}'.format(track_nr, sector_nr, track))
                        sector_nr = -1
                        track_nr = -1
                        trust = False
                    else:
                        print('\tFound track {} sector {} on track {}'.format(track_nr, sector_nr, track))
            elif byte_nr > 0:
                if byte_nr <= 256:
                    data_field.append(temp_byte)
                else:
                    #print('\tSector done at {}'.format(bitcount))
                    if track_nr != track or not trust:
                        print('\tBad header for track {} sector {}, reports track {}, or untrused sector'.format(track, sector_nr, track_nr))
                        if sectors[sector_nr+1][2]:
                            if sectors[sector_nr+1][1] == data_field:
                                sectors[sector_nr+1] = [False, data_field, not trust]
                            else:
                                sectors[sector_nr+1] = [False, data_field, True]
                    else:
                        if sectors[sector_nr+1][1] is not None and sectors[sector_nr+1][1] != data_field:
                            print('\tMismatching data for track {} sector {}'.format(sector_nr, track_nr))
                            sectors[sector_nr+1][2] = True
                        elif sectors[sector_nr+1][2]:
                            sectors[sector_nr+1] = [False, data_field, False]
                    track_nr = -1
                    sector_nr = -1
                    byte_nr = -1
                    trust = False

        if b == 'R' and byte_nr != -1:
            trust = False
            if sector_nr == -1:
                print('\tBad clock for track {} sector {} header, byte {} bit {}'.format(track, sector_nr, byte_nr, bit_nr))
            else:
                print('\tBad clock for track {} sector {} data, byte {} bit {}'.format(track, sector_nr, byte_nr, bit_nr))

    for s in sectors.values():
        if s[1] is None:
            print(data)
            break

    return sectors
