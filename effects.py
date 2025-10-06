import colors
import clock_effects

stop_flag = False

def set_stop_flag(value: bool):
    global stop_flag
    stop_flag = value


def allin(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.red_hue(i))
    strip.show()


def clock_timer(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.blue_hue(i*2))

def clock(strip):
    return clock_effects.clock(strip)


def clock2(strip):
    return clock_effects.clock2(strip)


def clock3(strip):
    return clock_effects.clock3(strip)


def clock4(strip):
    return clock_effects.clock4(strip)


def clock5(strip):
    return clock_effects.clock5(strip)


def clock6(strip):
    return clock_effects.clock6(strip)