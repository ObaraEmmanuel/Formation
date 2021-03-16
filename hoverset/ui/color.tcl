proc hsvToRgb {h s v} {
    set Hi [expr { int( double($h) / 60 ) % 6 }]
    set f [expr { double($h) / 60 - $Hi }]
    set s [expr { double($s)/100 }]
    set v [expr { double($v)/100 }]
    set p [expr { double($v) * (1 - $s) }]
    set q [expr { double($v) * (1 - $f * $s) }]
    set t [expr { double($v) * (1 - (1 - $f) * $s) }]
    switch -- $Hi {
        0 {
            set r $v
            set g $t
            set b $p
        }
        1 {
            set r $q
            set g $v
            set b $p
        }
        2 {
            set r $p
            set g $v
            set b $t
        }
        3 {
            set r $p
            set g $q
            set b $v
        }
        4 {
            set r $t
            set g $p
            set b $v
        }
        5 {
            set r $v
            set g $p
            set b $q
        }
        default {
            error "Wrong Hi value in hsvToRgb procedure! This should never happen!"
        }
    }
    set r [expr {round($r*255)}]
    set g [expr {round($g*255)}]
    set b [expr {round($b*255)}]
    return [list $r $g $b]
}

proc rgbToHsv {r g b} {
    set temp  [expr {min($r, $g, $b)}]
    set value [expr {max($r, $g, $b)}]
    set range [expr {$value-$temp}]
    if {$range == 0} {
        set hue 0
    } else {
        if {$value == $r} {
            set top [expr {$g-$b}]
            if {$g >= $b} {
                set angle 0
            } else {
                set angle 360
            }
        } elseif {$value == $g} {
            set top [expr {$b-$r}]
            set angle 120
        } elseif {$value == $b} {
            set top [expr {$r-$g}]
            set angle 240
        }
        set hue [expr { round( double($top) / $range * 60 + $angle ) }]
    }

    if {$value == 0} {
        set saturation 0
    } else {
        set saturation [expr { round( 100 - double($temp) / $value * 100 ) }]
    }
    set hsv [list $hue $saturation $value]
}

proc rgbToHex {rgb} {
    set hex [format "#%02x%02x%02x" [lindex $rgb 0] [lindex $rgb 1] [lindex $rgb 2]]
}

proc recolor_space {canvas hue} {
    set c 1
    for {set i 0} {$i <= 100} {incr i 2} {
        for {set j 100} {$j >= 0} {incr j -2} {
            set color [rgbToHex [hsvToRgb $hue $i $j]]
            $canvas itemconfigure $c -fill $color
            incr c
        }
    }
}

proc recolor_strip {canvas colors} {
    set i 1
    foreach c $colors {
        $canvas itemconfigure $i -fill $c
        incr i
    }
}