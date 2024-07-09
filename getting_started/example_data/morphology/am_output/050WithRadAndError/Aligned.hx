# Amira Script
remove -all
remove {physics.icol} {S29_final_done_Alison_zScale_40.am} {S30_final_done_Alison_zScale_40.am} {S31_final_done_Alison_zScale_40.am} {S32_final_done_Alison_zScale_40.am} {S33_final_done_Alison_zScale_40.am} {S24_final_done_Alison_zScale_40.am} {S25_final_done_Alison_zScale_40.am} {S27_final_done_Alison_zScale_40.am} {S28_final_done_Alison_zScale_40.am} {S22_final_done_Alison_zScale_40.am} {S23_final_done_Alison_zScale_40.am} {S26_final_done_Alison_zScale_40.am} {S18_final_done_Alison_zScale_40.am} {S19_final_done_Alison_zScale_40.am} {S20_final_done_Alison_zScale_40.am} {S21_final_done_Alison_zScale_40.am} {S11_final_done_zScale_40.am} {S12_final_done_zScale_40.am} {S13_final_done_Alison_zScale_40.am} {S14_final_done_Alison_zScale_40.am} {S15_final_done_Alison_zScale_40.am} {S16_final_done_Alison_zScale_40.am} {S17_final_done_Alison_zScale_40.am} {S34_final_downsampled_dendrites_done_zScale_40_aligned.am} {S35_final_downsampled_dendrites_done_zScale_40_aligned.am} {S36_final_downsampled_dendrites_done_zScale_40_aligned.am} {SpatialGraphView} {SpatialGraphView2} {SpatialGraphView3} {SpatialGraphView4} {SpatialGraphView5} {SpatialGraphView6} {SpatialGraphView7} {SpatialGraphView8} {SpatialGraphView9} {SpatialGraphView10} {SpatialGraphView11} {SpatialGraphView12} {SpatialGraphView13} {SpatialGraphView14} {SpatialGraphView15} {SpatialGraphView16} {SpatialGraphView17} {SpatialGraphView18} {SpatialGraphView19} {SpatialGraphView20} {SpatialGraphView21} {SpatialGraphView22} {SpatialGraphView23} {SpatialGraphView24} {SpatialGraphView25} {SpatialGraphView26}

# Create viewers
viewer setVertical 0

viewer 0 setBackgroundMode 0
viewer 0 setBackgroundColor 0 0 0
viewer 0 setBackgroundColor2 0.686275 0.701961 0.807843
viewer 0 setTransparencyType 5
viewer 0 setAutoRedraw 0
viewer 0 show
mainWindow show

set hideNewModules 1
[ load ${AMIRA_ROOT}/data/colormaps/physics.icol ] setLabel {physics.icol}
{physics.icol} setIconPosition 0 0
{physics.icol} setNoRemoveAll 1
{physics.icol} fire
{physics.icol} setMinMax 0 1
{physics.icol} {flags} setValue 1
{physics.icol} {shift} setMinMax -1 1
{physics.icol} {shift} setButtons 0
{physics.icol} {shift} setIncrement 0.133333
{physics.icol} {shift} setValue 0
{physics.icol} {shift} setSubMinMax -1 1
{physics.icol} {scale} setMinMax 0 1
{physics.icol} {scale} setButtons 0
{physics.icol} {scale} setIncrement 0.1
{physics.icol} {scale} setValue 1
{physics.icol} {scale} setSubMinMax 0 1
physics.icol fire
physics.icol setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S29_final_done_Alison_zScale_40.am ] setLabel {S29_final_done_Alison_zScale_40.am}
{S29_final_done_Alison_zScale_40.am} setIconPosition 12 236
S29_final_done_Alison_zScale_40.am setTransform 0.999914 0.0131216 0 0 -0.0131216 0.999914 0 0 0 0 0.999999 0 21.5008 29.0256 -120 1
S29_final_done_Alison_zScale_40.am fire
S29_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S30_final_done_Alison_zScale_40.am ] setLabel {S30_final_done_Alison_zScale_40.am}
{S30_final_done_Alison_zScale_40.am} setIconPosition 12 266
S30_final_done_Alison_zScale_40.am setTransform 0.99688 0.0789379 0 0 -0.0789379 0.99688 0 0 0 0 1 0 21.991 -10.9665 -80 1
S30_final_done_Alison_zScale_40.am fire
S30_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S31_final_done_Alison_zScale_40.am ] setLabel {S31_final_done_Alison_zScale_40.am}
{S31_final_done_Alison_zScale_40.am} setIconPosition 12 296
S31_final_done_Alison_zScale_40.am setTransform 0.997787 0.066498 0 0 -0.066498 0.997787 0 0 0 0 0.999999 0 -3.33759 -38.9517 -40 1
S31_final_done_Alison_zScale_40.am fire
S31_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S32_final_done_Alison_zScale_40.am ] setLabel {S32_final_done_Alison_zScale_40.am}
{S32_final_done_Alison_zScale_40.am} setIconPosition 12 326
S32_final_done_Alison_zScale_40.am fire
S32_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S33_final_done_Alison_zScale_40.am ] setLabel {S33_final_done_Alison_zScale_40.am}
{S33_final_done_Alison_zScale_40.am} setIconPosition 12 356
S33_final_done_Alison_zScale_40.am setTransform 0.991545 -0.129763 0 0 0.129763 0.991545 0 0 0 0 0.999999 0 -37.082 16.4679 40 1
S33_final_done_Alison_zScale_40.am fire
S33_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S24_final_done_Alison_zScale_40.am ] setLabel {S24_final_done_Alison_zScale_40.am}
{S24_final_done_Alison_zScale_40.am} setIconPosition 12 86
S24_final_done_Alison_zScale_40.am setTransform 0.998177 -0.0603346 0 0 0.0603346 0.998177 0 0 0 0 0.999999 0 30.2765 92.9345 -320 1
S24_final_done_Alison_zScale_40.am fire
S24_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S25_final_done_Alison_zScale_40.am ] setLabel {S25_final_done_Alison_zScale_40.am}
{S25_final_done_Alison_zScale_40.am} setIconPosition 12 116
S25_final_done_Alison_zScale_40.am setTransform 0.989911 -0.14169 0 0 0.14169 0.989911 0 0 0 0 1 0 -5.13791 113.041 -280 1
S25_final_done_Alison_zScale_40.am fire
S25_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S27_final_done_Alison_zScale_40.am ] setLabel {S27_final_done_Alison_zScale_40.am}
{S27_final_done_Alison_zScale_40.am} setIconPosition 12 176
S27_final_done_Alison_zScale_40.am setTransform 0.999724 -0.023499 0 0 0.023499 0.999724 0 0 0 0 1 0 16.0807 52.9691 -200 1
S27_final_done_Alison_zScale_40.am fire
S27_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S28_final_done_Alison_zScale_40.am ] setLabel {S28_final_done_Alison_zScale_40.am}
{S28_final_done_Alison_zScale_40.am} setIconPosition 12 206
S28_final_done_Alison_zScale_40.am setTransform 0.999316 -0.0369856 0 0 0.0369856 0.999316 0 0 0 0 1 0 10.8148 56.7287 -160 1
S28_final_done_Alison_zScale_40.am fire
S28_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S22_final_done_Alison_zScale_40.am ] setLabel {S22_final_done_Alison_zScale_40.am}
{S22_final_done_Alison_zScale_40.am} setIconPosition 12 27
S22_final_done_Alison_zScale_40.am setTransform 0.994567 -0.104096 0 0 0.104096 0.994567 0 0 0 0 1 0 15.4605 128.032 -400 1
S22_final_done_Alison_zScale_40.am fire
S22_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S23_final_done_Alison_zScale_40.am ] setLabel {S23_final_done_Alison_zScale_40.am}
{S23_final_done_Alison_zScale_40.am} setIconPosition 12 57
S23_final_done_Alison_zScale_40.am setTransform 0.981592 -0.19099 0 0 0.19099 0.981592 0 0 0 0 0.999999 0 -13.765 152.936 -360 1
S23_final_done_Alison_zScale_40.am fire
S23_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S26_final_done_Alison_zScale_40.am ] setLabel {S26_final_done_Alison_zScale_40.am}
{S26_final_done_Alison_zScale_40.am} setIconPosition 12 147
S26_final_done_Alison_zScale_40.am setTransform 0.989669 -0.143371 0 0 0.143371 0.989669 0 0 0 0 0.999999 0 -13.9274 104.024 -240 1
S26_final_done_Alison_zScale_40.am fire
S26_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S18_final_done_Alison_zScale_40.am ] setLabel {S18_final_done_Alison_zScale_40.am}
{S18_final_done_Alison_zScale_40.am} setIconPosition 13 -94
S18_final_done_Alison_zScale_40.am setTransform 0.973102 -0.230369 0 0 0.230369 0.973102 0 0 0 0 0.999999 0 17.6569 223.928 -560 1
S18_final_done_Alison_zScale_40.am fire
S18_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S19_final_done_Alison_zScale_40.am ] setLabel {S19_final_done_Alison_zScale_40.am}
{S19_final_done_Alison_zScale_40.am} setIconPosition 11 -64
S19_final_done_Alison_zScale_40.am setTransform 0.997184 -0.074998 0 0 0.074998 0.997184 0 0 0 0 1 0 48.9228 153.365 -520 1
S19_final_done_Alison_zScale_40.am fire
S19_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S20_final_done_Alison_zScale_40.am ] setLabel {S20_final_done_Alison_zScale_40.am}
{S20_final_done_Alison_zScale_40.am} setIconPosition 13 -34
S20_final_done_Alison_zScale_40.am setTransform 0.999285 -0.037787 0 0 0.037787 0.999285 0 0 0 0 0.999999 0 52.2153 127.378 -480 1
S20_final_done_Alison_zScale_40.am fire
S20_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S21_final_done_Alison_zScale_40.am ] setLabel {S21_final_done_Alison_zScale_40.am}
{S21_final_done_Alison_zScale_40.am} setIconPosition 13 -4
S21_final_done_Alison_zScale_40.am setTransform 0.999787 -0.0206599 0 0 0.0206599 0.999787 0 0 0 0 1 0 48.7704 127.236 -440 1
S21_final_done_Alison_zScale_40.am fire
S21_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S11_final_done_zScale_40.am ] setLabel {S11_final_done_zScale_40.am}
{S11_final_done_zScale_40.am} setIconPosition 13 -304
S11_final_done_zScale_40.am setTransform 0.995406 -0.0957431 0 0 0.0957431 0.995406 0 0 0 0 1 0 209.038 233.623 -840 1
S11_final_done_zScale_40.am fire
S11_final_done_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S12_final_done_zScale_40.am ] setLabel {S12_final_done_zScale_40.am}
{S12_final_done_zScale_40.am} setIconPosition 13 -274
S12_final_done_zScale_40.am setTransform 0.978227 -0.207539 0 0 0.207539 0.978227 0 0 0 0 1 0 152.833 375.495 -800 1
S12_final_done_zScale_40.am fire
S12_final_done_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S13_final_done_Alison_zScale_40.am ] setLabel {S13_final_done_Alison_zScale_40.am}
{S13_final_done_Alison_zScale_40.am} setIconPosition 13 -244
S13_final_done_Alison_zScale_40.am setTransform 0.973157 -0.230141 0 0 0.230141 0.973157 0 0 0 0 0.999999 0 51.9101 259.836 -760 1
S13_final_done_Alison_zScale_40.am fire
S13_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S14_final_done_Alison_zScale_40.am ] setLabel {S14_final_done_Alison_zScale_40.am}
{S14_final_done_Alison_zScale_40.am} setIconPosition 13 -214
S14_final_done_Alison_zScale_40.am setTransform 0.991582 -0.129477 0 0 0.129477 0.991582 0 0 0 0 1 0 56.7706 214.204 -720 1
S14_final_done_Alison_zScale_40.am fire
S14_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S15_final_done_Alison_zScale_40.am ] setLabel {S15_final_done_Alison_zScale_40.am}
{S15_final_done_Alison_zScale_40.am} setIconPosition 13 -184
S15_final_done_Alison_zScale_40.am setTransform 0.998754 -0.0499035 0 0 0.0499035 0.998754 0 0 0 0 1 0 88.972 193.809 -680 1
S15_final_done_Alison_zScale_40.am fire
S15_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S16_final_done_Alison_zScale_40.am ] setLabel {S16_final_done_Alison_zScale_40.am}
{S16_final_done_Alison_zScale_40.am} setIconPosition 13 -154
S16_final_done_Alison_zScale_40.am setTransform 0.996977 -0.0777029 0 0 0.0777029 0.996977 0 0 0 0 1 0 58.1335 184.755 -640 1
S16_final_done_Alison_zScale_40.am fire
S16_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/S17_final_done_Alison_zScale_40.am ] setLabel {S17_final_done_Alison_zScale_40.am}
{S17_final_done_Alison_zScale_40.am} setIconPosition 13 -124
S17_final_done_Alison_zScale_40.am setTransform 0.995038 -0.0994923 0 0 0.0994923 0.995038 0 0 0 0 1 0 54.6011 174.822 -600 1
S17_final_done_Alison_zScale_40.am fire
S17_final_done_Alison_zScale_40.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/aligned/S34_final_downsampled_dendrites_done_zScale_40_aligned_ascii.am ] setLabel {S34_final_downsampled_dendrites_done_zScale_40_aligned.am}
{S34_final_downsampled_dendrites_done_zScale_40_aligned.am} setIconPosition 20 386
S34_final_downsampled_dendrites_done_zScale_40_aligned.am setTransform 0.994983 -0.100034 0 0 0.100034 0.994983 0 0 0 0 0.999997 0 -16.1855 19.4307 79.9997 1
S34_final_downsampled_dendrites_done_zScale_40_aligned.am fire
S34_final_downsampled_dendrites_done_zScale_40_aligned.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/aligned/S35_final_downsampled_dendrites_done_zScale_40_aligned_ascii.am ] setLabel {S35_final_downsampled_dendrites_done_zScale_40_aligned.am}
{S35_final_downsampled_dendrites_done_zScale_40_aligned.am} setIconPosition 20 416
S35_final_downsampled_dendrites_done_zScale_40_aligned.am setTransform 0.999052 0.0435142 0 0 -0.0435142 0.999052 0 0 0 0 1 0 10.5192 -36.5757 120 1
S35_final_downsampled_dendrites_done_zScale_40_aligned.am fire
S35_final_downsampled_dendrites_done_zScale_40_aligned.am setViewerMask 16383

set hideNewModules 0
[ load ${SCRIPTDIR}/aligned/S36_final_downsampled_dendrites_done_zScale_40_aligned_ascii.am ] setLabel {S36_final_downsampled_dendrites_done_zScale_40_aligned.am}
{S36_final_downsampled_dendrites_done_zScale_40_aligned.am} setIconPosition 20 446
S36_final_downsampled_dendrites_done_zScale_40_aligned.am setTransform 0.988391 -0.151937 0 0 0.151937 0.988391 0 0 0 0 1 0 -56.9004 29.9898 160 1
S36_final_downsampled_dendrites_done_zScale_40_aligned.am fire
S36_final_downsampled_dendrites_done_zScale_40_aligned.am setViewerMask 16383

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView}
{SpatialGraphView} setIconPosition 372 296
{SpatialGraphView} {data} connect S31_final_done_Alison_zScale_40.am
{SpatialGraphView} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView} {nodeColormap} setLocalRange 0
{SpatialGraphView} {nodeColormap} connect physics.icol
{SpatialGraphView} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView} {segmentColormap} setLocalRange 0
{SpatialGraphView} {segmentColormap} connect physics.icol
{SpatialGraphView} fire
{SpatialGraphView} {itemsToShow} setValue 0 0
{SpatialGraphView} {itemsToShow} setValue 1 1
{SpatialGraphView} {nodeScale} setIndex 0 0
{SpatialGraphView} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView} {nodeScaleFactor} setButtons 0
{SpatialGraphView} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView} {nodeScaleFactor} setValue 2.5967
{SpatialGraphView} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView} {nodeColoring} setIndex 0 0
{SpatialGraphView} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView} {segmentStyle} setValue 0 1
{SpatialGraphView} {segmentStyle} setValue 1 0
{SpatialGraphView} {segmentStyle} setValue 2 0
{SpatialGraphView} {tubeScale} setIndex 0 0
{SpatialGraphView} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView} {tubeScaleFactor} setButtons 0
{SpatialGraphView} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView} {tubeScaleFactor} setValue 0.2
{SpatialGraphView} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView} {segmentWidth} setMinMax 0 10
{SpatialGraphView} {segmentWidth} setButtons 0
{SpatialGraphView} {segmentWidth} setIncrement 0.666667
{SpatialGraphView} {segmentWidth} setValue 1
{SpatialGraphView} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView} {segmentColoring} setIndex 0 1
{SpatialGraphView} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView} {segmentColor} setColor 0 1 0 0
{SpatialGraphView} {segmentColor} setAlpha 0 -1
{SpatialGraphView} {pointSize} setMinMax 0 15
{SpatialGraphView} {pointSize} setButtons 0
{SpatialGraphView} {pointSize} setIncrement 1
{SpatialGraphView} {pointSize} setValue 4
{SpatialGraphView} {pointSize} setSubMinMax 0 15
{SpatialGraphView} setVisibility HIJMPLPPBPDPAAAAAOCOBPOB HIJMPLPPJPDAAAAAJHKICDNN
SpatialGraphView fire
SpatialGraphView setViewerMask 16383
SpatialGraphView setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView2}
{SpatialGraphView2} setIconPosition 372 326
{SpatialGraphView2} {data} connect S32_final_done_Alison_zScale_40.am
{SpatialGraphView2} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView2} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView2} {nodeColormap} setLocalRange 0
{SpatialGraphView2} {nodeColormap} connect physics.icol
{SpatialGraphView2} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView2} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView2} {segmentColormap} setLocalRange 0
{SpatialGraphView2} {segmentColormap} connect physics.icol
{SpatialGraphView2} fire
{SpatialGraphView2} {itemsToShow} setValue 0 0
{SpatialGraphView2} {itemsToShow} setValue 1 1
{SpatialGraphView2} {nodeScale} setIndex 0 0
{SpatialGraphView2} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView2} {nodeScaleFactor} setButtons 0
{SpatialGraphView2} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView2} {nodeScaleFactor} setValue 2.7048
{SpatialGraphView2} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView2} {nodeColoring} setIndex 0 0
{SpatialGraphView2} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView2} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView2} {segmentStyle} setValue 0 1
{SpatialGraphView2} {segmentStyle} setValue 1 0
{SpatialGraphView2} {segmentStyle} setValue 2 0
{SpatialGraphView2} {tubeScale} setIndex 0 0
{SpatialGraphView2} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView2} {tubeScaleFactor} setButtons 0
{SpatialGraphView2} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView2} {tubeScaleFactor} setValue 0.2
{SpatialGraphView2} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView2} {segmentWidth} setMinMax 0 10
{SpatialGraphView2} {segmentWidth} setButtons 0
{SpatialGraphView2} {segmentWidth} setIncrement 0.666667
{SpatialGraphView2} {segmentWidth} setValue 1
{SpatialGraphView2} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView2} {segmentColoring} setIndex 0 1
{SpatialGraphView2} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView2} {segmentColor} setColor 0 0 1 0
{SpatialGraphView2} {segmentColor} setAlpha 0 -1
{SpatialGraphView2} {pointSize} setMinMax 0 15
{SpatialGraphView2} {pointSize} setButtons 0
{SpatialGraphView2} {pointSize} setIncrement 1
{SpatialGraphView2} {pointSize} setValue 4
{SpatialGraphView2} {pointSize} setSubMinMax 0 15
{SpatialGraphView2} setVisibility HIJMPLPPJPDAAAAAJHKICDNN HIJMPLPPJPDIAAAADBCBCHNJ
SpatialGraphView2 fire
SpatialGraphView2 setViewerMask 16383
SpatialGraphView2 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView3}
{SpatialGraphView3} setIconPosition 370 356
{SpatialGraphView3} {data} connect S33_final_done_Alison_zScale_40.am
{SpatialGraphView3} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView3} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView3} {nodeColormap} setLocalRange 0
{SpatialGraphView3} {nodeColormap} connect physics.icol
{SpatialGraphView3} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView3} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView3} {segmentColormap} setLocalRange 0
{SpatialGraphView3} {segmentColormap} connect physics.icol
{SpatialGraphView3} fire
{SpatialGraphView3} {itemsToShow} setValue 0 0
{SpatialGraphView3} {itemsToShow} setValue 1 1
{SpatialGraphView3} {nodeScale} setIndex 0 0
{SpatialGraphView3} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView3} {nodeScaleFactor} setButtons 0
{SpatialGraphView3} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView3} {nodeScaleFactor} setValue 2.40028
{SpatialGraphView3} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView3} {nodeColoring} setIndex 0 0
{SpatialGraphView3} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView3} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView3} {segmentStyle} setValue 0 1
{SpatialGraphView3} {segmentStyle} setValue 1 0
{SpatialGraphView3} {segmentStyle} setValue 2 0
{SpatialGraphView3} {tubeScale} setIndex 0 0
{SpatialGraphView3} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView3} {tubeScaleFactor} setButtons 0
{SpatialGraphView3} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView3} {tubeScaleFactor} setValue 0.2
{SpatialGraphView3} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView3} {segmentWidth} setMinMax 0 10
{SpatialGraphView3} {segmentWidth} setButtons 0
{SpatialGraphView3} {segmentWidth} setIncrement 0.666667
{SpatialGraphView3} {segmentWidth} setValue 1
{SpatialGraphView3} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView3} {segmentColoring} setIndex 0 1
{SpatialGraphView3} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView3} {segmentColor} setColor 0 0 1 0
{SpatialGraphView3} {segmentColor} setAlpha 0 -1
{SpatialGraphView3} {pointSize} setMinMax 0 15
{SpatialGraphView3} {pointSize} setButtons 0
{SpatialGraphView3} {pointSize} setIncrement 1
{SpatialGraphView3} {pointSize} setValue 4
{SpatialGraphView3} {pointSize} setSubMinMax 0 15
{SpatialGraphView3} setVisibility HIJMPLPPBPBDAAAANBECBDON HIJMPLPPBPDLAAAACKPLBHOJ
SpatialGraphView3 fire
SpatialGraphView3 setViewerMask 16383
SpatialGraphView3 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView4}
{SpatialGraphView4} setIconPosition 371 266
{SpatialGraphView4} {data} connect S30_final_done_Alison_zScale_40.am
{SpatialGraphView4} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView4} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView4} {nodeColormap} setLocalRange 0
{SpatialGraphView4} {nodeColormap} connect physics.icol
{SpatialGraphView4} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView4} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView4} {segmentColormap} setLocalRange 0
{SpatialGraphView4} {segmentColormap} connect physics.icol
{SpatialGraphView4} fire
{SpatialGraphView4} {itemsToShow} setValue 0 0
{SpatialGraphView4} {itemsToShow} setValue 1 1
{SpatialGraphView4} {nodeScale} setIndex 0 0
{SpatialGraphView4} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView4} {nodeScaleFactor} setButtons 0
{SpatialGraphView4} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView4} {nodeScaleFactor} setValue 2.39476
{SpatialGraphView4} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView4} {nodeColoring} setIndex 0 0
{SpatialGraphView4} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView4} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView4} {segmentStyle} setValue 0 1
{SpatialGraphView4} {segmentStyle} setValue 1 0
{SpatialGraphView4} {segmentStyle} setValue 2 0
{SpatialGraphView4} {tubeScale} setIndex 0 0
{SpatialGraphView4} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView4} {tubeScaleFactor} setButtons 0
{SpatialGraphView4} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView4} {tubeScaleFactor} setValue 0.2
{SpatialGraphView4} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView4} {segmentWidth} setMinMax 0 10
{SpatialGraphView4} {segmentWidth} setButtons 0
{SpatialGraphView4} {segmentWidth} setIncrement 0.666667
{SpatialGraphView4} {segmentWidth} setValue 1
{SpatialGraphView4} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView4} {segmentColoring} setIndex 0 1
{SpatialGraphView4} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView4} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView4} {segmentColor} setAlpha 0 -1
{SpatialGraphView4} {pointSize} setMinMax 0 15
{SpatialGraphView4} {pointSize} setButtons 0
{SpatialGraphView4} {pointSize} setIncrement 1
{SpatialGraphView4} {pointSize} setValue 4
{SpatialGraphView4} {pointSize} setSubMinMax 0 15
{SpatialGraphView4} setVisibility HIJMPLPPBPBFAAAAIHIIAPPB HIJMPLPPBPBDAAAANBECBDON
SpatialGraphView4 fire
SpatialGraphView4 setViewerMask 16383
SpatialGraphView4 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView5}
{SpatialGraphView5} setIconPosition 371 236
{SpatialGraphView5} {data} connect S29_final_done_Alison_zScale_40.am
{SpatialGraphView5} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView5} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView5} {nodeColormap} setLocalRange 0
{SpatialGraphView5} {nodeColormap} connect physics.icol
{SpatialGraphView5} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView5} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView5} {segmentColormap} setLocalRange 0
{SpatialGraphView5} {segmentColormap} connect physics.icol
{SpatialGraphView5} fire
{SpatialGraphView5} {itemsToShow} setValue 0 0
{SpatialGraphView5} {itemsToShow} setValue 1 1
{SpatialGraphView5} {nodeScale} setIndex 0 0
{SpatialGraphView5} {nodeScaleFactor} setMinMax 0 47
{SpatialGraphView5} {nodeScaleFactor} setButtons 0
{SpatialGraphView5} {nodeScaleFactor} setIncrement 3.13333
{SpatialGraphView5} {nodeScaleFactor} setValue 2.33266
{SpatialGraphView5} {nodeScaleFactor} setSubMinMax 0 47
{SpatialGraphView5} {nodeColoring} setIndex 0 0
{SpatialGraphView5} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView5} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView5} {segmentStyle} setValue 0 1
{SpatialGraphView5} {segmentStyle} setValue 1 0
{SpatialGraphView5} {segmentStyle} setValue 2 0
{SpatialGraphView5} {tubeScale} setIndex 0 0
{SpatialGraphView5} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView5} {tubeScaleFactor} setButtons 0
{SpatialGraphView5} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView5} {tubeScaleFactor} setValue 0.2
{SpatialGraphView5} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView5} {segmentWidth} setMinMax 0 10
{SpatialGraphView5} {segmentWidth} setButtons 0
{SpatialGraphView5} {segmentWidth} setIncrement 0.666667
{SpatialGraphView5} {segmentWidth} setValue 1
{SpatialGraphView5} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView5} {segmentColoring} setIndex 0 1
{SpatialGraphView5} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView5} {segmentColor} setColor 0 1 0 0
{SpatialGraphView5} {segmentColor} setAlpha 0 -1
{SpatialGraphView5} {pointSize} setMinMax 0 15
{SpatialGraphView5} {pointSize} setButtons 0
{SpatialGraphView5} {pointSize} setIncrement 1
{SpatialGraphView5} {pointSize} setValue 4
{SpatialGraphView5} {pointSize} setSubMinMax 0 15
{SpatialGraphView5} setVisibility HIJMPLPPBPACAACDOEAHPJ HIJMPLPPBPABAAENLOALPF
SpatialGraphView5 fire
SpatialGraphView5 setViewerMask 16383
SpatialGraphView5 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView6}
{SpatialGraphView6} setIconPosition 371 206
{SpatialGraphView6} {data} connect S28_final_done_Alison_zScale_40.am
{SpatialGraphView6} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView6} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView6} {nodeColormap} setLocalRange 0
{SpatialGraphView6} {nodeColormap} connect physics.icol
{SpatialGraphView6} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView6} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView6} {segmentColormap} setLocalRange 0
{SpatialGraphView6} {segmentColormap} connect physics.icol
{SpatialGraphView6} fire
{SpatialGraphView6} {itemsToShow} setValue 0 0
{SpatialGraphView6} {itemsToShow} setValue 1 1
{SpatialGraphView6} {nodeScale} setIndex 0 0
{SpatialGraphView6} {nodeScaleFactor} setMinMax 0 45
{SpatialGraphView6} {nodeScaleFactor} setButtons 0
{SpatialGraphView6} {nodeScaleFactor} setIncrement 3
{SpatialGraphView6} {nodeScaleFactor} setValue 2.24388
{SpatialGraphView6} {nodeScaleFactor} setSubMinMax 0 45
{SpatialGraphView6} {nodeColoring} setIndex 0 0
{SpatialGraphView6} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView6} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView6} {segmentStyle} setValue 0 1
{SpatialGraphView6} {segmentStyle} setValue 1 0
{SpatialGraphView6} {segmentStyle} setValue 2 0
{SpatialGraphView6} {tubeScale} setIndex 0 0
{SpatialGraphView6} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView6} {tubeScaleFactor} setButtons 0
{SpatialGraphView6} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView6} {tubeScaleFactor} setValue 0.2
{SpatialGraphView6} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView6} {segmentWidth} setMinMax 0 10
{SpatialGraphView6} {segmentWidth} setButtons 0
{SpatialGraphView6} {segmentWidth} setIncrement 0.666667
{SpatialGraphView6} {segmentWidth} setValue 1
{SpatialGraphView6} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView6} {segmentColoring} setIndex 0 1
{SpatialGraphView6} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView6} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView6} {segmentColor} setAlpha 0 -1
{SpatialGraphView6} {pointSize} setMinMax 0 15
{SpatialGraphView6} {pointSize} setButtons 0
{SpatialGraphView6} {pointSize} setIncrement 1
{SpatialGraphView6} {pointSize} setValue 4
{SpatialGraphView6} {pointSize} setSubMinMax 0 15
{SpatialGraphView6} setVisibility HIJMPLPPBPABAAENLOALPF HIJMPLPPBPABAAENLOALPF
SpatialGraphView6 fire
SpatialGraphView6 setViewerMask 16383
SpatialGraphView6 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView7}
{SpatialGraphView7} setIconPosition 371 175
{SpatialGraphView7} {data} connect S27_final_done_Alison_zScale_40.am
{SpatialGraphView7} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView7} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView7} {nodeColormap} setLocalRange 0
{SpatialGraphView7} {nodeColormap} connect physics.icol
{SpatialGraphView7} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView7} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView7} {segmentColormap} setLocalRange 0
{SpatialGraphView7} {segmentColormap} connect physics.icol
{SpatialGraphView7} fire
{SpatialGraphView7} {itemsToShow} setValue 0 0
{SpatialGraphView7} {itemsToShow} setValue 1 1
{SpatialGraphView7} {nodeScale} setIndex 0 0
{SpatialGraphView7} {nodeScaleFactor} setMinMax 0 33
{SpatialGraphView7} {nodeScaleFactor} setButtons 0
{SpatialGraphView7} {nodeScaleFactor} setIncrement 2.2
{SpatialGraphView7} {nodeScaleFactor} setValue 1.62104
{SpatialGraphView7} {nodeScaleFactor} setSubMinMax 0 33
{SpatialGraphView7} {nodeColoring} setIndex 0 0
{SpatialGraphView7} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView7} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView7} {segmentStyle} setValue 0 1
{SpatialGraphView7} {segmentStyle} setValue 1 0
{SpatialGraphView7} {segmentStyle} setValue 2 0
{SpatialGraphView7} {tubeScale} setIndex 0 0
{SpatialGraphView7} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView7} {tubeScaleFactor} setButtons 0
{SpatialGraphView7} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView7} {tubeScaleFactor} setValue 0.2
{SpatialGraphView7} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView7} {segmentWidth} setMinMax 0 10
{SpatialGraphView7} {segmentWidth} setButtons 0
{SpatialGraphView7} {segmentWidth} setIncrement 0.666667
{SpatialGraphView7} {segmentWidth} setValue 1
{SpatialGraphView7} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView7} {segmentColoring} setIndex 0 1
{SpatialGraphView7} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView7} {segmentColor} setColor 0 1 0 0
{SpatialGraphView7} {segmentColor} setAlpha 0 -1
{SpatialGraphView7} {pointSize} setMinMax 0 15
{SpatialGraphView7} {pointSize} setButtons 0
{SpatialGraphView7} {pointSize} setIncrement 1
{SpatialGraphView7} {pointSize} setValue 4
{SpatialGraphView7} {pointSize} setSubMinMax 0 15
{SpatialGraphView7} setVisibility HIJMPLPPPPPPHPAAAJPKADPN HIJMPLPPBPACAACDOEAHPJ
SpatialGraphView7 fire
SpatialGraphView7 setViewerMask 16383
SpatialGraphView7 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView8}
{SpatialGraphView8} setIconPosition 372 147
{SpatialGraphView8} {data} connect S26_final_done_Alison_zScale_40.am
{SpatialGraphView8} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView8} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView8} {nodeColormap} setLocalRange 0
{SpatialGraphView8} {nodeColormap} connect physics.icol
{SpatialGraphView8} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView8} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView8} {segmentColormap} setLocalRange 0
{SpatialGraphView8} {segmentColormap} connect physics.icol
{SpatialGraphView8} fire
{SpatialGraphView8} {itemsToShow} setValue 0 0
{SpatialGraphView8} {itemsToShow} setValue 1 1
{SpatialGraphView8} {nodeScale} setIndex 0 0
{SpatialGraphView8} {nodeScaleFactor} setMinMax 0 36
{SpatialGraphView8} {nodeScaleFactor} setButtons 0
{SpatialGraphView8} {nodeScaleFactor} setIncrement 2.4
{SpatialGraphView8} {nodeScaleFactor} setValue 1.75996
{SpatialGraphView8} {nodeScaleFactor} setSubMinMax 0 36
{SpatialGraphView8} {nodeColoring} setIndex 0 0
{SpatialGraphView8} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView8} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView8} {segmentStyle} setValue 0 1
{SpatialGraphView8} {segmentStyle} setValue 1 0
{SpatialGraphView8} {segmentStyle} setValue 2 0
{SpatialGraphView8} {tubeScale} setIndex 0 0
{SpatialGraphView8} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView8} {tubeScaleFactor} setButtons 0
{SpatialGraphView8} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView8} {tubeScaleFactor} setValue 0.2
{SpatialGraphView8} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView8} {segmentWidth} setMinMax 0 10
{SpatialGraphView8} {segmentWidth} setButtons 0
{SpatialGraphView8} {segmentWidth} setIncrement 0.666667
{SpatialGraphView8} {segmentWidth} setValue 1
{SpatialGraphView8} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView8} {segmentColoring} setIndex 0 2
{SpatialGraphView8} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView8} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView8} {segmentColor} setAlpha 0 -1
{SpatialGraphView8} {pointSize} setMinMax 0 15
{SpatialGraphView8} {pointSize} setButtons 0
{SpatialGraphView8} {pointSize} setIncrement 1
{SpatialGraphView8} {pointSize} setValue 4
{SpatialGraphView8} {pointSize} setSubMinMax 0 15
{SpatialGraphView8} setVisibility HIJMPLPPBPACAACDOEAHPJ HIJMPLPPBPACAACDOEAHPJ
SpatialGraphView8 fire
SpatialGraphView8 setViewerMask 16383
SpatialGraphView8 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView9}
{SpatialGraphView9} setIconPosition 371 116
{SpatialGraphView9} {data} connect S25_final_done_Alison_zScale_40.am
{SpatialGraphView9} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView9} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView9} {nodeColormap} setLocalRange 0
{SpatialGraphView9} {nodeColormap} connect physics.icol
{SpatialGraphView9} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView9} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView9} {segmentColormap} setLocalRange 0
{SpatialGraphView9} {segmentColormap} connect physics.icol
{SpatialGraphView9} fire
{SpatialGraphView9} {itemsToShow} setValue 0 0
{SpatialGraphView9} {itemsToShow} setValue 1 1
{SpatialGraphView9} {nodeScale} setIndex 0 0
{SpatialGraphView9} {nodeScaleFactor} setMinMax 0 40
{SpatialGraphView9} {nodeScaleFactor} setButtons 0
{SpatialGraphView9} {nodeScaleFactor} setIncrement 2.66667
{SpatialGraphView9} {nodeScaleFactor} setValue 1.96926
{SpatialGraphView9} {nodeScaleFactor} setSubMinMax 0 40
{SpatialGraphView9} {nodeColoring} setIndex 0 0
{SpatialGraphView9} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView9} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView9} {segmentStyle} setValue 0 1
{SpatialGraphView9} {segmentStyle} setValue 1 0
{SpatialGraphView9} {segmentStyle} setValue 2 0
{SpatialGraphView9} {tubeScale} setIndex 0 0
{SpatialGraphView9} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView9} {tubeScaleFactor} setButtons 0
{SpatialGraphView9} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView9} {tubeScaleFactor} setValue 0.2
{SpatialGraphView9} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView9} {segmentWidth} setMinMax 0 10
{SpatialGraphView9} {segmentWidth} setButtons 0
{SpatialGraphView9} {segmentWidth} setIncrement 0.666667
{SpatialGraphView9} {segmentWidth} setValue 1
{SpatialGraphView9} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView9} {segmentColoring} setIndex 0 1
{SpatialGraphView9} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView9} {segmentColor} setColor 0 1 0 0
{SpatialGraphView9} {segmentColor} setAlpha 0 -1
{SpatialGraphView9} {pointSize} setMinMax 0 15
{SpatialGraphView9} {pointSize} setButtons 0
{SpatialGraphView9} {pointSize} setIncrement 1
{SpatialGraphView9} {pointSize} setValue 4
{SpatialGraphView9} {pointSize} setSubMinMax 0 15
{SpatialGraphView9} setVisibility HIJMPLPPBPACAACDOEAHPJ HIJMPLPPBPACAACDOEAHPJ
SpatialGraphView9 fire
SpatialGraphView9 setViewerMask 16383
SpatialGraphView9 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView10}
{SpatialGraphView10} setIconPosition 364 86
{SpatialGraphView10} {data} connect S24_final_done_Alison_zScale_40.am
{SpatialGraphView10} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView10} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView10} {nodeColormap} setLocalRange 0
{SpatialGraphView10} {nodeColormap} connect physics.icol
{SpatialGraphView10} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView10} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView10} {segmentColormap} setLocalRange 0
{SpatialGraphView10} {segmentColormap} connect physics.icol
{SpatialGraphView10} fire
{SpatialGraphView10} {itemsToShow} setValue 0 0
{SpatialGraphView10} {itemsToShow} setValue 1 1
{SpatialGraphView10} {nodeScale} setIndex 0 0
{SpatialGraphView10} {nodeScaleFactor} setMinMax 0 36
{SpatialGraphView10} {nodeScaleFactor} setButtons 0
{SpatialGraphView10} {nodeScaleFactor} setIncrement 2.4
{SpatialGraphView10} {nodeScaleFactor} setValue 1.79906
{SpatialGraphView10} {nodeScaleFactor} setSubMinMax 0 36
{SpatialGraphView10} {nodeColoring} setIndex 0 0
{SpatialGraphView10} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView10} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView10} {segmentStyle} setValue 0 1
{SpatialGraphView10} {segmentStyle} setValue 1 0
{SpatialGraphView10} {segmentStyle} setValue 2 0
{SpatialGraphView10} {tubeScale} setIndex 0 0
{SpatialGraphView10} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView10} {tubeScaleFactor} setButtons 0
{SpatialGraphView10} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView10} {tubeScaleFactor} setValue 0.2
{SpatialGraphView10} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView10} {segmentWidth} setMinMax 0 10
{SpatialGraphView10} {segmentWidth} setButtons 0
{SpatialGraphView10} {segmentWidth} setIncrement 0.666667
{SpatialGraphView10} {segmentWidth} setValue 1
{SpatialGraphView10} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView10} {segmentColoring} setIndex 0 1
{SpatialGraphView10} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView10} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView10} {segmentColor} setAlpha 0 -1
{SpatialGraphView10} {pointSize} setMinMax 0 15
{SpatialGraphView10} {pointSize} setButtons 0
{SpatialGraphView10} {pointSize} setIncrement 1
{SpatialGraphView10} {pointSize} setValue 4
{SpatialGraphView10} {pointSize} setSubMinMax 0 15
{SpatialGraphView10} setVisibility HIJMPLPPBPACAACDOEAHPJ HIJMPLPPBPACAACDOEAHPJ
SpatialGraphView10 fire
SpatialGraphView10 setViewerMask 16383
SpatialGraphView10 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView11}
{SpatialGraphView11} setIconPosition 365 57
{SpatialGraphView11} {data} connect S23_final_done_Alison_zScale_40.am
{SpatialGraphView11} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView11} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView11} {nodeColormap} setLocalRange 0
{SpatialGraphView11} {nodeColormap} connect physics.icol
{SpatialGraphView11} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView11} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView11} {segmentColormap} setLocalRange 0
{SpatialGraphView11} {segmentColormap} connect physics.icol
{SpatialGraphView11} fire
{SpatialGraphView11} {itemsToShow} setValue 0 0
{SpatialGraphView11} {itemsToShow} setValue 1 1
{SpatialGraphView11} {nodeScale} setIndex 0 0
{SpatialGraphView11} {nodeScaleFactor} setMinMax 0 40
{SpatialGraphView11} {nodeScaleFactor} setButtons 0
{SpatialGraphView11} {nodeScaleFactor} setIncrement 2.66667
{SpatialGraphView11} {nodeScaleFactor} setValue 1.98398
{SpatialGraphView11} {nodeScaleFactor} setSubMinMax 0 40
{SpatialGraphView11} {nodeColoring} setIndex 0 0
{SpatialGraphView11} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView11} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView11} {segmentStyle} setValue 0 1
{SpatialGraphView11} {segmentStyle} setValue 1 0
{SpatialGraphView11} {segmentStyle} setValue 2 0
{SpatialGraphView11} {tubeScale} setIndex 0 0
{SpatialGraphView11} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView11} {tubeScaleFactor} setButtons 0
{SpatialGraphView11} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView11} {tubeScaleFactor} setValue 0.2
{SpatialGraphView11} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView11} {segmentWidth} setMinMax 0 10
{SpatialGraphView11} {segmentWidth} setButtons 0
{SpatialGraphView11} {segmentWidth} setIncrement 0.666667
{SpatialGraphView11} {segmentWidth} setValue 1
{SpatialGraphView11} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView11} {segmentColoring} setIndex 0 1
{SpatialGraphView11} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView11} {segmentColor} setColor 0 1 0 0
{SpatialGraphView11} {segmentColor} setAlpha 0 -1
{SpatialGraphView11} {pointSize} setMinMax 0 15
{SpatialGraphView11} {pointSize} setButtons 0
{SpatialGraphView11} {pointSize} setIncrement 1
{SpatialGraphView11} {pointSize} setValue 4
{SpatialGraphView11} {pointSize} setSubMinMax 0 15
{SpatialGraphView11} setVisibility HIJMPLPPBPBFAAAAIHIIAPPB HIJMPLPPBPBFAAAAIHIIAPPB
SpatialGraphView11 fire
SpatialGraphView11 setViewerMask 16383
SpatialGraphView11 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView12}
{SpatialGraphView12} setIconPosition 362 27
{SpatialGraphView12} {data} connect S22_final_done_Alison_zScale_40.am
{SpatialGraphView12} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView12} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView12} {nodeColormap} setLocalRange 0
{SpatialGraphView12} {nodeColormap} connect physics.icol
{SpatialGraphView12} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView12} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView12} {segmentColormap} setLocalRange 0
{SpatialGraphView12} {segmentColormap} connect physics.icol
{SpatialGraphView12} fire
{SpatialGraphView12} {itemsToShow} setValue 0 0
{SpatialGraphView12} {itemsToShow} setValue 1 1
{SpatialGraphView12} {nodeScale} setIndex 0 0
{SpatialGraphView12} {nodeScaleFactor} setMinMax 0 49
{SpatialGraphView12} {nodeScaleFactor} setButtons 0
{SpatialGraphView12} {nodeScaleFactor} setIncrement 3.26667
{SpatialGraphView12} {nodeScaleFactor} setValue 2.42098
{SpatialGraphView12} {nodeScaleFactor} setSubMinMax 0 49
{SpatialGraphView12} {nodeColoring} setIndex 0 0
{SpatialGraphView12} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView12} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView12} {segmentStyle} setValue 0 1
{SpatialGraphView12} {segmentStyle} setValue 1 0
{SpatialGraphView12} {segmentStyle} setValue 2 0
{SpatialGraphView12} {tubeScale} setIndex 0 0
{SpatialGraphView12} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView12} {tubeScaleFactor} setButtons 0
{SpatialGraphView12} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView12} {tubeScaleFactor} setValue 0.2
{SpatialGraphView12} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView12} {segmentWidth} setMinMax 0 10
{SpatialGraphView12} {segmentWidth} setButtons 0
{SpatialGraphView12} {segmentWidth} setIncrement 0.666667
{SpatialGraphView12} {segmentWidth} setValue 1
{SpatialGraphView12} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView12} {segmentColoring} setIndex 0 1
{SpatialGraphView12} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView12} {segmentColor} setColor 0 0 1 0.227273
{SpatialGraphView12} {segmentColor} setAlpha 0 -1
{SpatialGraphView12} {pointSize} setMinMax 0 15
{SpatialGraphView12} {pointSize} setButtons 0
{SpatialGraphView12} {pointSize} setIncrement 1
{SpatialGraphView12} {pointSize} setValue 4
{SpatialGraphView12} {pointSize} setSubMinMax 0 15
{SpatialGraphView12} setVisibility HIJMPLPPBPBDAAAANBECBDON HIJMPLPPBPBDAAAANBECBDON
SpatialGraphView12 fire
SpatialGraphView12 setViewerMask 16383
SpatialGraphView12 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView13}
{SpatialGraphView13} setIconPosition 362 -4
{SpatialGraphView13} {data} connect S21_final_done_Alison_zScale_40.am
{SpatialGraphView13} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView13} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView13} {nodeColormap} setLocalRange 0
{SpatialGraphView13} {nodeColormap} connect physics.icol
{SpatialGraphView13} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView13} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView13} {segmentColormap} setLocalRange 0
{SpatialGraphView13} {segmentColormap} connect physics.icol
{SpatialGraphView13} fire
{SpatialGraphView13} {itemsToShow} setValue 0 0
{SpatialGraphView13} {itemsToShow} setValue 1 1
{SpatialGraphView13} {nodeScale} setIndex 0 0
{SpatialGraphView13} {nodeScaleFactor} setMinMax 0 56
{SpatialGraphView13} {nodeScaleFactor} setButtons 0
{SpatialGraphView13} {nodeScaleFactor} setIncrement 3.73333
{SpatialGraphView13} {nodeScaleFactor} setValue 2.79036
{SpatialGraphView13} {nodeScaleFactor} setSubMinMax 0 56
{SpatialGraphView13} {nodeColoring} setIndex 0 0
{SpatialGraphView13} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView13} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView13} {segmentStyle} setValue 0 1
{SpatialGraphView13} {segmentStyle} setValue 1 0
{SpatialGraphView13} {segmentStyle} setValue 2 0
{SpatialGraphView13} {tubeScale} setIndex 0 0
{SpatialGraphView13} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView13} {tubeScaleFactor} setButtons 0
{SpatialGraphView13} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView13} {tubeScaleFactor} setValue 0.2
{SpatialGraphView13} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView13} {segmentWidth} setMinMax 0 10
{SpatialGraphView13} {segmentWidth} setButtons 0
{SpatialGraphView13} {segmentWidth} setIncrement 0.666667
{SpatialGraphView13} {segmentWidth} setValue 1
{SpatialGraphView13} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView13} {segmentColoring} setIndex 0 1
{SpatialGraphView13} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView13} {segmentColor} setColor 0 1 0 0
{SpatialGraphView13} {segmentColor} setAlpha 0 -1
{SpatialGraphView13} {pointSize} setMinMax 0 15
{SpatialGraphView13} {pointSize} setButtons 0
{SpatialGraphView13} {pointSize} setIncrement 1
{SpatialGraphView13} {pointSize} setValue 4
{SpatialGraphView13} {pointSize} setSubMinMax 0 15
{SpatialGraphView13} setVisibility HIJMPLPPBPDLAAAACKPLBHOJ HIJMPLPPBPDLAAAACKPLBHOJ
SpatialGraphView13 fire
SpatialGraphView13 setViewerMask 16383
SpatialGraphView13 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView14}
{SpatialGraphView14} setIconPosition 362 -34
{SpatialGraphView14} {data} connect S20_final_done_Alison_zScale_40.am
{SpatialGraphView14} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView14} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView14} {nodeColormap} setLocalRange 0
{SpatialGraphView14} {nodeColormap} connect physics.icol
{SpatialGraphView14} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView14} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView14} {segmentColormap} setLocalRange 0
{SpatialGraphView14} {segmentColormap} connect physics.icol
{SpatialGraphView14} fire
{SpatialGraphView14} {itemsToShow} setValue 0 0
{SpatialGraphView14} {itemsToShow} setValue 1 1
{SpatialGraphView14} {nodeScale} setIndex 0 0
{SpatialGraphView14} {nodeScaleFactor} setMinMax 0 46
{SpatialGraphView14} {nodeScaleFactor} setButtons 0
{SpatialGraphView14} {nodeScaleFactor} setIncrement 3.06667
{SpatialGraphView14} {nodeScaleFactor} setValue 2.2724
{SpatialGraphView14} {nodeScaleFactor} setSubMinMax 0 46
{SpatialGraphView14} {nodeColoring} setIndex 0 0
{SpatialGraphView14} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView14} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView14} {segmentStyle} setValue 0 1
{SpatialGraphView14} {segmentStyle} setValue 1 0
{SpatialGraphView14} {segmentStyle} setValue 2 0
{SpatialGraphView14} {tubeScale} setIndex 0 0
{SpatialGraphView14} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView14} {tubeScaleFactor} setButtons 0
{SpatialGraphView14} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView14} {tubeScaleFactor} setValue 0.2
{SpatialGraphView14} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView14} {segmentWidth} setMinMax 0 10
{SpatialGraphView14} {segmentWidth} setButtons 0
{SpatialGraphView14} {segmentWidth} setIncrement 0.666667
{SpatialGraphView14} {segmentWidth} setValue 1
{SpatialGraphView14} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView14} {segmentColoring} setIndex 0 1
{SpatialGraphView14} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView14} {segmentColor} setColor 0 0 1 0.136364
{SpatialGraphView14} {segmentColor} setAlpha 0 -1
{SpatialGraphView14} {pointSize} setMinMax 0 15
{SpatialGraphView14} {pointSize} setButtons 0
{SpatialGraphView14} {pointSize} setIncrement 1
{SpatialGraphView14} {pointSize} setValue 4
{SpatialGraphView14} {pointSize} setSubMinMax 0 15
{SpatialGraphView14} setVisibility HIJMPLPPBPDLAAAACKPLBHOJ HIJMPLPPBPDHAAAAJEJFBLOF
SpatialGraphView14 fire
SpatialGraphView14 setViewerMask 16383
SpatialGraphView14 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView15}
{SpatialGraphView15} setIconPosition 363 -64
{SpatialGraphView15} {data} connect S19_final_done_Alison_zScale_40.am
{SpatialGraphView15} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView15} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView15} {nodeColormap} setLocalRange 0
{SpatialGraphView15} {nodeColormap} connect physics.icol
{SpatialGraphView15} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView15} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView15} {segmentColormap} setLocalRange 0
{SpatialGraphView15} {segmentColormap} connect physics.icol
{SpatialGraphView15} fire
{SpatialGraphView15} {itemsToShow} setValue 0 0
{SpatialGraphView15} {itemsToShow} setValue 1 1
{SpatialGraphView15} {nodeScale} setIndex 0 0
{SpatialGraphView15} {nodeScaleFactor} setMinMax 0 40
{SpatialGraphView15} {nodeScaleFactor} setButtons 0
{SpatialGraphView15} {nodeScaleFactor} setIncrement 2.66667
{SpatialGraphView15} {nodeScaleFactor} setValue 1.96834
{SpatialGraphView15} {nodeScaleFactor} setSubMinMax 0 40
{SpatialGraphView15} {nodeColoring} setIndex 0 0
{SpatialGraphView15} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView15} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView15} {segmentStyle} setValue 0 1
{SpatialGraphView15} {segmentStyle} setValue 1 0
{SpatialGraphView15} {segmentStyle} setValue 2 0
{SpatialGraphView15} {tubeScale} setIndex 0 0
{SpatialGraphView15} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView15} {tubeScaleFactor} setButtons 0
{SpatialGraphView15} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView15} {tubeScaleFactor} setValue 0.2
{SpatialGraphView15} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView15} {segmentWidth} setMinMax 0 10
{SpatialGraphView15} {segmentWidth} setButtons 0
{SpatialGraphView15} {segmentWidth} setIncrement 0.666667
{SpatialGraphView15} {segmentWidth} setValue 1
{SpatialGraphView15} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView15} {segmentColoring} setIndex 0 1
{SpatialGraphView15} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView15} {segmentColor} setColor 0 1 0 0
{SpatialGraphView15} {segmentColor} setAlpha 0 -1
{SpatialGraphView15} {pointSize} setMinMax 0 15
{SpatialGraphView15} {pointSize} setButtons 0
{SpatialGraphView15} {pointSize} setIncrement 1
{SpatialGraphView15} {pointSize} setValue 4
{SpatialGraphView15} {pointSize} setSubMinMax 0 15
{SpatialGraphView15} setVisibility HIJMPLPPBPBDAAAANBECBDON HIJMPLPPBPBDAAAANBECBDON
SpatialGraphView15 fire
SpatialGraphView15 setViewerMask 16383
SpatialGraphView15 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView16}
{SpatialGraphView16} setIconPosition 363 -94
{SpatialGraphView16} {data} connect S18_final_done_Alison_zScale_40.am
{SpatialGraphView16} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView16} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView16} {nodeColormap} setLocalRange 0
{SpatialGraphView16} {nodeColormap} connect physics.icol
{SpatialGraphView16} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView16} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView16} {segmentColormap} setLocalRange 0
{SpatialGraphView16} {segmentColormap} connect physics.icol
{SpatialGraphView16} fire
{SpatialGraphView16} {itemsToShow} setValue 0 0
{SpatialGraphView16} {itemsToShow} setValue 1 1
{SpatialGraphView16} {nodeScale} setIndex 0 0
{SpatialGraphView16} {nodeScaleFactor} setMinMax 0 38
{SpatialGraphView16} {nodeScaleFactor} setButtons 0
{SpatialGraphView16} {nodeScaleFactor} setIncrement 2.53333
{SpatialGraphView16} {nodeScaleFactor} setValue 1.85058
{SpatialGraphView16} {nodeScaleFactor} setSubMinMax 0 38
{SpatialGraphView16} {nodeColoring} setIndex 0 0
{SpatialGraphView16} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView16} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView16} {segmentStyle} setValue 0 1
{SpatialGraphView16} {segmentStyle} setValue 1 0
{SpatialGraphView16} {segmentStyle} setValue 2 0
{SpatialGraphView16} {tubeScale} setIndex 0 0
{SpatialGraphView16} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView16} {tubeScaleFactor} setButtons 0
{SpatialGraphView16} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView16} {tubeScaleFactor} setValue 0.2
{SpatialGraphView16} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView16} {segmentWidth} setMinMax 0 10
{SpatialGraphView16} {segmentWidth} setButtons 0
{SpatialGraphView16} {segmentWidth} setIncrement 0.666667
{SpatialGraphView16} {segmentWidth} setValue 1
{SpatialGraphView16} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView16} {segmentColoring} setIndex 0 1
{SpatialGraphView16} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView16} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView16} {segmentColor} setAlpha 0 -1
{SpatialGraphView16} {pointSize} setMinMax 0 15
{SpatialGraphView16} {pointSize} setButtons 0
{SpatialGraphView16} {pointSize} setIncrement 1
{SpatialGraphView16} {pointSize} setValue 4
{SpatialGraphView16} {pointSize} setSubMinMax 0 15
{SpatialGraphView16} setVisibility HIJMPLPPBPBDAAAANBECBDON HIJMPLPPBPDLAAAACKPLBHOJ
SpatialGraphView16 fire
SpatialGraphView16 setViewerMask 16383
SpatialGraphView16 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView17}
{SpatialGraphView17} setIconPosition 363 -124
{SpatialGraphView17} {data} connect S17_final_done_Alison_zScale_40.am
{SpatialGraphView17} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView17} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView17} {nodeColormap} setLocalRange 0
{SpatialGraphView17} {nodeColormap} connect physics.icol
{SpatialGraphView17} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView17} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView17} {segmentColormap} setLocalRange 0
{SpatialGraphView17} {segmentColormap} connect physics.icol
{SpatialGraphView17} fire
{SpatialGraphView17} {itemsToShow} setValue 0 0
{SpatialGraphView17} {itemsToShow} setValue 1 1
{SpatialGraphView17} {nodeScale} setIndex 0 0
{SpatialGraphView17} {nodeScaleFactor} setMinMax 0 41
{SpatialGraphView17} {nodeScaleFactor} setButtons 0
{SpatialGraphView17} {nodeScaleFactor} setIncrement 2.73333
{SpatialGraphView17} {nodeScaleFactor} setValue 2.00468
{SpatialGraphView17} {nodeScaleFactor} setSubMinMax 0 41
{SpatialGraphView17} {nodeColoring} setIndex 0 0
{SpatialGraphView17} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView17} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView17} {segmentStyle} setValue 0 1
{SpatialGraphView17} {segmentStyle} setValue 1 0
{SpatialGraphView17} {segmentStyle} setValue 2 0
{SpatialGraphView17} {tubeScale} setIndex 0 0
{SpatialGraphView17} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView17} {tubeScaleFactor} setButtons 0
{SpatialGraphView17} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView17} {tubeScaleFactor} setValue 0.2
{SpatialGraphView17} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView17} {segmentWidth} setMinMax 0 10
{SpatialGraphView17} {segmentWidth} setButtons 0
{SpatialGraphView17} {segmentWidth} setIncrement 0.666667
{SpatialGraphView17} {segmentWidth} setValue 1
{SpatialGraphView17} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView17} {segmentColoring} setIndex 0 1
{SpatialGraphView17} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView17} {segmentColor} setColor 0 1 0 0
{SpatialGraphView17} {segmentColor} setAlpha 0 -1
{SpatialGraphView17} {pointSize} setMinMax 0 15
{SpatialGraphView17} {pointSize} setButtons 0
{SpatialGraphView17} {pointSize} setIncrement 1
{SpatialGraphView17} {pointSize} setValue 4
{SpatialGraphView17} {pointSize} setSubMinMax 0 15
{SpatialGraphView17} setVisibility HIJMPLPPBPBDAAAANBECBDON HIJMPLPPBPDLAAAACKPLBHOJ
SpatialGraphView17 fire
SpatialGraphView17 setViewerMask 16383
SpatialGraphView17 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView18}
{SpatialGraphView18} setIconPosition 362 -154
{SpatialGraphView18} {data} connect S16_final_done_Alison_zScale_40.am
{SpatialGraphView18} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView18} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView18} {nodeColormap} setLocalRange 0
{SpatialGraphView18} {nodeColormap} connect physics.icol
{SpatialGraphView18} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView18} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView18} {segmentColormap} setLocalRange 0
{SpatialGraphView18} {segmentColormap} connect physics.icol
{SpatialGraphView18} fire
{SpatialGraphView18} {itemsToShow} setValue 0 0
{SpatialGraphView18} {itemsToShow} setValue 1 1
{SpatialGraphView18} {nodeScale} setIndex 0 0
{SpatialGraphView18} {nodeScaleFactor} setMinMax 0 44
{SpatialGraphView18} {nodeScaleFactor} setButtons 0
{SpatialGraphView18} {nodeScaleFactor} setIncrement 2.93333
{SpatialGraphView18} {nodeScaleFactor} setValue 2.18408
{SpatialGraphView18} {nodeScaleFactor} setSubMinMax 0 44
{SpatialGraphView18} {nodeColoring} setIndex 0 0
{SpatialGraphView18} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView18} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView18} {segmentStyle} setValue 0 1
{SpatialGraphView18} {segmentStyle} setValue 1 0
{SpatialGraphView18} {segmentStyle} setValue 2 0
{SpatialGraphView18} {tubeScale} setIndex 0 0
{SpatialGraphView18} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView18} {tubeScaleFactor} setButtons 0
{SpatialGraphView18} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView18} {tubeScaleFactor} setValue 0.2
{SpatialGraphView18} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView18} {segmentWidth} setMinMax 0 10
{SpatialGraphView18} {segmentWidth} setButtons 0
{SpatialGraphView18} {segmentWidth} setIncrement 0.666667
{SpatialGraphView18} {segmentWidth} setValue 1
{SpatialGraphView18} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView18} {segmentColoring} setIndex 0 1
{SpatialGraphView18} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView18} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView18} {segmentColor} setAlpha 0 -1
{SpatialGraphView18} {pointSize} setMinMax 0 15
{SpatialGraphView18} {pointSize} setButtons 0
{SpatialGraphView18} {pointSize} setIncrement 1
{SpatialGraphView18} {pointSize} setValue 4
{SpatialGraphView18} {pointSize} setSubMinMax 0 15
{SpatialGraphView18} setVisibility HIJMPLPPBPDHAAAAJEJFBLOF HIJMPLPPBPDHAAAAJEJFBLOF
SpatialGraphView18 fire
SpatialGraphView18 setViewerMask 16383
SpatialGraphView18 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView19}
{SpatialGraphView19} setIconPosition 362 -184
{SpatialGraphView19} {data} connect S15_final_done_Alison_zScale_40.am
{SpatialGraphView19} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView19} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView19} {nodeColormap} setLocalRange 0
{SpatialGraphView19} {nodeColormap} connect physics.icol
{SpatialGraphView19} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView19} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView19} {segmentColormap} setLocalRange 0
{SpatialGraphView19} {segmentColormap} connect physics.icol
{SpatialGraphView19} fire
{SpatialGraphView19} {itemsToShow} setValue 0 0
{SpatialGraphView19} {itemsToShow} setValue 1 1
{SpatialGraphView19} {nodeScale} setIndex 0 0
{SpatialGraphView19} {nodeScaleFactor} setMinMax 0 50
{SpatialGraphView19} {nodeScaleFactor} setButtons 0
{SpatialGraphView19} {nodeScaleFactor} setIncrement 3.33333
{SpatialGraphView19} {nodeScaleFactor} setValue 2.49734
{SpatialGraphView19} {nodeScaleFactor} setSubMinMax 0 50
{SpatialGraphView19} {nodeColoring} setIndex 0 0
{SpatialGraphView19} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView19} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView19} {segmentStyle} setValue 0 1
{SpatialGraphView19} {segmentStyle} setValue 1 0
{SpatialGraphView19} {segmentStyle} setValue 2 0
{SpatialGraphView19} {tubeScale} setIndex 0 0
{SpatialGraphView19} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView19} {tubeScaleFactor} setButtons 0
{SpatialGraphView19} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView19} {tubeScaleFactor} setValue 0.2
{SpatialGraphView19} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView19} {segmentWidth} setMinMax 0 10
{SpatialGraphView19} {segmentWidth} setButtons 0
{SpatialGraphView19} {segmentWidth} setIncrement 0.666667
{SpatialGraphView19} {segmentWidth} setValue 1
{SpatialGraphView19} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView19} {segmentColoring} setIndex 0 1
{SpatialGraphView19} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView19} {segmentColor} setColor 0 1 0 0
{SpatialGraphView19} {segmentColor} setAlpha 0 -1
{SpatialGraphView19} {pointSize} setMinMax 0 15
{SpatialGraphView19} {pointSize} setButtons 0
{SpatialGraphView19} {pointSize} setIncrement 1
{SpatialGraphView19} {pointSize} setValue 4
{SpatialGraphView19} {pointSize} setSubMinMax 0 15
{SpatialGraphView19} setVisibility HIJMPLPPBPDLAAAACKPLBHOJ HIJMPLPPBPDLAAAACKPLBHOJ
SpatialGraphView19 fire
SpatialGraphView19 setViewerMask 16383
SpatialGraphView19 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView20}
{SpatialGraphView20} setIconPosition 362 -214
{SpatialGraphView20} {data} connect S14_final_done_Alison_zScale_40.am
{SpatialGraphView20} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView20} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView20} {nodeColormap} setLocalRange 0
{SpatialGraphView20} {nodeColormap} connect physics.icol
{SpatialGraphView20} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView20} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView20} {segmentColormap} setLocalRange 0
{SpatialGraphView20} {segmentColormap} connect physics.icol
{SpatialGraphView20} fire
{SpatialGraphView20} {itemsToShow} setValue 0 0
{SpatialGraphView20} {itemsToShow} setValue 1 1
{SpatialGraphView20} {nodeScale} setIndex 0 0
{SpatialGraphView20} {nodeScaleFactor} setMinMax 0 53
{SpatialGraphView20} {nodeScaleFactor} setButtons 0
{SpatialGraphView20} {nodeScaleFactor} setIncrement 3.53333
{SpatialGraphView20} {nodeScaleFactor} setValue 2.61694
{SpatialGraphView20} {nodeScaleFactor} setSubMinMax 0 53
{SpatialGraphView20} {nodeColoring} setIndex 0 0
{SpatialGraphView20} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView20} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView20} {segmentStyle} setValue 0 1
{SpatialGraphView20} {segmentStyle} setValue 1 0
{SpatialGraphView20} {segmentStyle} setValue 2 0
{SpatialGraphView20} {tubeScale} setIndex 0 0
{SpatialGraphView20} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView20} {tubeScaleFactor} setButtons 0
{SpatialGraphView20} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView20} {tubeScaleFactor} setValue 0.2
{SpatialGraphView20} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView20} {segmentWidth} setMinMax 0 10
{SpatialGraphView20} {segmentWidth} setButtons 0
{SpatialGraphView20} {segmentWidth} setIncrement 0.666667
{SpatialGraphView20} {segmentWidth} setValue 1
{SpatialGraphView20} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView20} {segmentColoring} setIndex 0 1
{SpatialGraphView20} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView20} {segmentColor} setColor 0 0 1 0
{SpatialGraphView20} {segmentColor} setAlpha 0 -1
{SpatialGraphView20} {pointSize} setMinMax 0 15
{SpatialGraphView20} {pointSize} setButtons 0
{SpatialGraphView20} {pointSize} setIncrement 1
{SpatialGraphView20} {pointSize} setValue 4
{SpatialGraphView20} {pointSize} setSubMinMax 0 15
{SpatialGraphView20} setVisibility HIJMPLPPBPBFAAAAIHIIAPPB HIJMPLPPBPBFAAAAIHIIAPPB
SpatialGraphView20 fire
SpatialGraphView20 setViewerMask 16383
SpatialGraphView20 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView21}
{SpatialGraphView21} setIconPosition 362 -244
{SpatialGraphView21} {data} connect S13_final_done_Alison_zScale_40.am
{SpatialGraphView21} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView21} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView21} {nodeColormap} setLocalRange 0
{SpatialGraphView21} {nodeColormap} connect physics.icol
{SpatialGraphView21} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView21} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView21} {segmentColormap} setLocalRange 0
{SpatialGraphView21} {segmentColormap} connect physics.icol
{SpatialGraphView21} fire
{SpatialGraphView21} {itemsToShow} setValue 0 0
{SpatialGraphView21} {itemsToShow} setValue 1 1
{SpatialGraphView21} {nodeScale} setIndex 0 0
{SpatialGraphView21} {nodeScaleFactor} setMinMax 0 51
{SpatialGraphView21} {nodeScaleFactor} setButtons 0
{SpatialGraphView21} {nodeScaleFactor} setIncrement 3.4
{SpatialGraphView21} {nodeScaleFactor} setValue 2.53322
{SpatialGraphView21} {nodeScaleFactor} setSubMinMax 0 51
{SpatialGraphView21} {nodeColoring} setIndex 0 0
{SpatialGraphView21} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView21} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView21} {segmentStyle} setValue 0 1
{SpatialGraphView21} {segmentStyle} setValue 1 0
{SpatialGraphView21} {segmentStyle} setValue 2 0
{SpatialGraphView21} {tubeScale} setIndex 0 0
{SpatialGraphView21} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView21} {tubeScaleFactor} setButtons 0
{SpatialGraphView21} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView21} {tubeScaleFactor} setValue 0.2
{SpatialGraphView21} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView21} {segmentWidth} setMinMax 0 10
{SpatialGraphView21} {segmentWidth} setButtons 0
{SpatialGraphView21} {segmentWidth} setIncrement 0.666667
{SpatialGraphView21} {segmentWidth} setValue 1
{SpatialGraphView21} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView21} {segmentColoring} setIndex 0 1
{SpatialGraphView21} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView21} {segmentColor} setColor 0 1 0 0
{SpatialGraphView21} {segmentColor} setAlpha 0 -1
{SpatialGraphView21} {pointSize} setMinMax 0 15
{SpatialGraphView21} {pointSize} setButtons 0
{SpatialGraphView21} {pointSize} setIncrement 1
{SpatialGraphView21} {pointSize} setValue 4
{SpatialGraphView21} {pointSize} setSubMinMax 0 15
{SpatialGraphView21} setVisibility HIJMPLPPBPDLAAAACKPLBHOJ HIJMPLPPBPDLAAAACKPLBHOJ
SpatialGraphView21 fire
SpatialGraphView21 setViewerMask 16383
SpatialGraphView21 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView22}
{SpatialGraphView22} setIconPosition 359 -274
{SpatialGraphView22} {data} connect S12_final_done_zScale_40.am
{SpatialGraphView22} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView22} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView22} {nodeColormap} setLocalRange 0
{SpatialGraphView22} {nodeColormap} connect physics.icol
{SpatialGraphView22} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView22} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView22} {segmentColormap} setLocalRange 0
{SpatialGraphView22} {segmentColormap} connect physics.icol
{SpatialGraphView22} fire
{SpatialGraphView22} {itemsToShow} setValue 0 0
{SpatialGraphView22} {itemsToShow} setValue 1 1
{SpatialGraphView22} {nodeScale} setIndex 0 0
{SpatialGraphView22} {nodeScaleFactor} setMinMax 0 40
{SpatialGraphView22} {nodeScaleFactor} setButtons 0
{SpatialGraphView22} {nodeScaleFactor} setIncrement 2.66667
{SpatialGraphView22} {nodeScaleFactor} setValue 1.9803
{SpatialGraphView22} {nodeScaleFactor} setSubMinMax 0 40
{SpatialGraphView22} {nodeColoring} setIndex 0 0
{SpatialGraphView22} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView22} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView22} {segmentStyle} setValue 0 1
{SpatialGraphView22} {segmentStyle} setValue 1 0
{SpatialGraphView22} {segmentStyle} setValue 2 0
{SpatialGraphView22} {tubeScale} setIndex 0 0
{SpatialGraphView22} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView22} {tubeScaleFactor} setButtons 0
{SpatialGraphView22} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView22} {tubeScaleFactor} setValue 0.2
{SpatialGraphView22} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView22} {segmentWidth} setMinMax 0 10
{SpatialGraphView22} {segmentWidth} setButtons 0
{SpatialGraphView22} {segmentWidth} setIncrement 0.666667
{SpatialGraphView22} {segmentWidth} setValue 1
{SpatialGraphView22} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView22} {segmentColoring} setIndex 0 1
{SpatialGraphView22} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView22} {segmentColor} setColor 0 0 1 0.0909092
{SpatialGraphView22} {segmentColor} setAlpha 0 -1
{SpatialGraphView22} {pointSize} setMinMax 0 15
{SpatialGraphView22} {pointSize} setButtons 0
{SpatialGraphView22} {pointSize} setIncrement 1
{SpatialGraphView22} {pointSize} setValue 4
{SpatialGraphView22} {pointSize} setSubMinMax 0 15
{SpatialGraphView22} setVisibility HIJMPLPPBPACAACDOEAHPJ HIJMPLPPBPACAACDOEAHPJ
SpatialGraphView22 fire
SpatialGraphView22 setViewerMask 16383
SpatialGraphView22 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView23}
{SpatialGraphView23} setIconPosition 364 -304
{SpatialGraphView23} {data} connect S11_final_done_zScale_40.am
{SpatialGraphView23} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView23} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView23} {nodeColormap} setLocalRange 0
{SpatialGraphView23} {nodeColormap} connect physics.icol
{SpatialGraphView23} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView23} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView23} {segmentColormap} setLocalRange 0
{SpatialGraphView23} {segmentColormap} connect physics.icol
{SpatialGraphView23} fire
{SpatialGraphView23} {itemsToShow} setValue 0 0
{SpatialGraphView23} {itemsToShow} setValue 1 1
{SpatialGraphView23} {nodeScale} setIndex 0 0
{SpatialGraphView23} {nodeScaleFactor} setMinMax 0 50
{SpatialGraphView23} {nodeScaleFactor} setButtons 0
{SpatialGraphView23} {nodeScaleFactor} setIncrement 3.33333
{SpatialGraphView23} {nodeScaleFactor} setValue 2.48446
{SpatialGraphView23} {nodeScaleFactor} setSubMinMax 0 50
{SpatialGraphView23} {nodeColoring} setIndex 0 0
{SpatialGraphView23} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView23} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView23} {segmentStyle} setValue 0 1
{SpatialGraphView23} {segmentStyle} setValue 1 0
{SpatialGraphView23} {segmentStyle} setValue 2 0
{SpatialGraphView23} {tubeScale} setIndex 0 0
{SpatialGraphView23} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView23} {tubeScaleFactor} setButtons 0
{SpatialGraphView23} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView23} {tubeScaleFactor} setValue 0.2
{SpatialGraphView23} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView23} {segmentWidth} setMinMax 0 10
{SpatialGraphView23} {segmentWidth} setButtons 0
{SpatialGraphView23} {segmentWidth} setIncrement 0.666667
{SpatialGraphView23} {segmentWidth} setValue 1
{SpatialGraphView23} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView23} {segmentColoring} setIndex 0 1
{SpatialGraphView23} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView23} {segmentColor} setColor 0 1 0 0
{SpatialGraphView23} {segmentColor} setAlpha 0 -1
{SpatialGraphView23} {pointSize} setMinMax 0 15
{SpatialGraphView23} {pointSize} setButtons 0
{SpatialGraphView23} {pointSize} setIncrement 1
{SpatialGraphView23} {pointSize} setValue 4
{SpatialGraphView23} {pointSize} setSubMinMax 0 15
{SpatialGraphView23} setVisibility HIJMPLPPBPACAACDOEAHPJ HIJMPLPPBPABAAENLOALPF
SpatialGraphView23 fire
SpatialGraphView23 setViewerMask 16383
SpatialGraphView23 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView24}
{SpatialGraphView24} setIconPosition 377 386
{SpatialGraphView24} {data} connect S34_final_downsampled_dendrites_done_zScale_40_aligned.am
{SpatialGraphView24} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView24} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView24} {nodeColormap} setLocalRange 0
{SpatialGraphView24} {nodeColormap} connect physics.icol
{SpatialGraphView24} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView24} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView24} {segmentColormap} setLocalRange 0
{SpatialGraphView24} {segmentColormap} connect physics.icol
{SpatialGraphView24} fire
{SpatialGraphView24} {itemsToShow} setValue 0 0
{SpatialGraphView24} {itemsToShow} setValue 1 1
{SpatialGraphView24} {nodeScale} setIndex 0 0
{SpatialGraphView24} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView24} {nodeScaleFactor} setButtons 0
{SpatialGraphView24} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView24} {nodeScaleFactor} setValue 1.84322
{SpatialGraphView24} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView24} {nodeColoring} setIndex 0 0
{SpatialGraphView24} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView24} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView24} {segmentStyle} setValue 0 1
{SpatialGraphView24} {segmentStyle} setValue 1 0
{SpatialGraphView24} {segmentStyle} setValue 2 0
{SpatialGraphView24} {tubeScale} setIndex 0 0
{SpatialGraphView24} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView24} {tubeScaleFactor} setButtons 0
{SpatialGraphView24} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView24} {tubeScaleFactor} setValue 0.2
{SpatialGraphView24} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView24} {segmentWidth} setMinMax 0 10
{SpatialGraphView24} {segmentWidth} setButtons 0
{SpatialGraphView24} {segmentWidth} setIncrement 0.666667
{SpatialGraphView24} {segmentWidth} setValue 1
{SpatialGraphView24} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView24} {segmentColoring} setIndex 0 2
{SpatialGraphView24} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView24} {segmentColor} setColor 0 0 1 0
{SpatialGraphView24} {segmentColor} setAlpha 0 -1
{SpatialGraphView24} {pointSize} setMinMax 0 15
{SpatialGraphView24} {pointSize} setButtons 0
{SpatialGraphView24} {pointSize} setIncrement 1
{SpatialGraphView24} {pointSize} setValue 4
{SpatialGraphView24} {pointSize} setSubMinMax 0 15
{SpatialGraphView24} setVisibility HIJMPLPPBPABAAENLOALPF HIJMPLPPBPBFAAAAIHIIAPPB
SpatialGraphView24 fire
SpatialGraphView24 setViewerMask 16383
SpatialGraphView24 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView25}
{SpatialGraphView25} setIconPosition 373 416
{SpatialGraphView25} {data} connect S35_final_downsampled_dendrites_done_zScale_40_aligned.am
{SpatialGraphView25} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView25} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView25} {nodeColormap} setLocalRange 0
{SpatialGraphView25} {nodeColormap} connect physics.icol
{SpatialGraphView25} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView25} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView25} {segmentColormap} setLocalRange 0
{SpatialGraphView25} {segmentColormap} connect physics.icol
{SpatialGraphView25} fire
{SpatialGraphView25} {itemsToShow} setValue 0 0
{SpatialGraphView25} {itemsToShow} setValue 1 1
{SpatialGraphView25} {nodeScale} setIndex 0 0
{SpatialGraphView25} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView25} {nodeScaleFactor} setButtons 0
{SpatialGraphView25} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView25} {nodeScaleFactor} setValue 1.25672
{SpatialGraphView25} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView25} {nodeColoring} setIndex 0 0
{SpatialGraphView25} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView25} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView25} {segmentStyle} setValue 0 1
{SpatialGraphView25} {segmentStyle} setValue 1 0
{SpatialGraphView25} {segmentStyle} setValue 2 0
{SpatialGraphView25} {tubeScale} setIndex 0 0
{SpatialGraphView25} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView25} {tubeScaleFactor} setButtons 0
{SpatialGraphView25} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView25} {tubeScaleFactor} setValue 0.2
{SpatialGraphView25} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView25} {segmentWidth} setMinMax 0 10
{SpatialGraphView25} {segmentWidth} setButtons 0
{SpatialGraphView25} {segmentWidth} setIncrement 0.666667
{SpatialGraphView25} {segmentWidth} setValue 1
{SpatialGraphView25} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView25} {segmentColoring} setIndex 0 2
{SpatialGraphView25} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView25} {segmentColor} setColor 0 0 1 0
{SpatialGraphView25} {segmentColor} setAlpha 0 -1
{SpatialGraphView25} {pointSize} setMinMax 0 15
{SpatialGraphView25} {pointSize} setButtons 0
{SpatialGraphView25} {pointSize} setIncrement 1
{SpatialGraphView25} {pointSize} setValue 4
{SpatialGraphView25} {pointSize} setSubMinMax 0 15
{SpatialGraphView25} setVisibility HIJMPLPPPPPPHPAAAJPKADPN HIJMPLPPPPPPHPAAAJPKADPN
SpatialGraphView25 fire
SpatialGraphView25 setViewerMask 16383
SpatialGraphView25 setPickable 1

set hideNewModules 0
create {HxSpatialGraphView} {SpatialGraphView26}
{SpatialGraphView26} setIconPosition 374 445
{SpatialGraphView26} {data} connect S36_final_downsampled_dendrites_done_zScale_40_aligned.am
{SpatialGraphView26} {nodeColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView26} {nodeColormap} setDefaultAlpha 0.500000
{SpatialGraphView26} {nodeColormap} setLocalRange 0
{SpatialGraphView26} {nodeColormap} connect physics.icol
{SpatialGraphView26} {segmentColormap} setDefaultColor 1 0.8 0.5
{SpatialGraphView26} {segmentColormap} setDefaultAlpha 0.500000
{SpatialGraphView26} {segmentColormap} setLocalRange 0
{SpatialGraphView26} {segmentColormap} connect physics.icol
{SpatialGraphView26} fire
{SpatialGraphView26} {itemsToShow} setValue 0 0
{SpatialGraphView26} {itemsToShow} setValue 1 1
{SpatialGraphView26} {nodeScale} setIndex 0 0
{SpatialGraphView26} {nodeScaleFactor} setMinMax 0 55
{SpatialGraphView26} {nodeScaleFactor} setButtons 0
{SpatialGraphView26} {nodeScaleFactor} setIncrement 3.66667
{SpatialGraphView26} {nodeScaleFactor} setValue 1.1707
{SpatialGraphView26} {nodeScaleFactor} setSubMinMax 0 55
{SpatialGraphView26} {nodeColoring} setIndex 0 0
{SpatialGraphView26} {nodeLabelColoringOptions} setValue 0
{SpatialGraphView26} {nodeColor} setColor 0 0.8 0.8 0.8
{SpatialGraphView26} {segmentStyle} setValue 0 1
{SpatialGraphView26} {segmentStyle} setValue 1 0
{SpatialGraphView26} {segmentStyle} setValue 2 0
{SpatialGraphView26} {tubeScale} setIndex 0 0
{SpatialGraphView26} {tubeScaleFactor} setMinMax 0 10
{SpatialGraphView26} {tubeScaleFactor} setButtons 0
{SpatialGraphView26} {tubeScaleFactor} setIncrement 0.666667
{SpatialGraphView26} {tubeScaleFactor} setValue 0.2
{SpatialGraphView26} {tubeScaleFactor} setSubMinMax 0 10
{SpatialGraphView26} {segmentWidth} setMinMax 0 10
{SpatialGraphView26} {segmentWidth} setButtons 0
{SpatialGraphView26} {segmentWidth} setIncrement 0.666667
{SpatialGraphView26} {segmentWidth} setValue 1
{SpatialGraphView26} {segmentWidth} setSubMinMax 0 10
{SpatialGraphView26} {segmentColoring} setIndex 0 2
{SpatialGraphView26} {segmentLabelColoringOptions} setValue 0
{SpatialGraphView26} {segmentColor} setColor 0 0 1 0
{SpatialGraphView26} {segmentColor} setAlpha 0 -1
{SpatialGraphView26} {pointSize} setMinMax 0 15
{SpatialGraphView26} {pointSize} setButtons 0
{SpatialGraphView26} {pointSize} setIncrement 1
{SpatialGraphView26} {pointSize} setValue 4
{SpatialGraphView26} {pointSize} setSubMinMax 0 15
{SpatialGraphView26} setVisibility HIJMPLPPPPPPHPAAAJPKADPN HIJMPLPPPPPPHPAAAJPKADPN
SpatialGraphView26 fire
SpatialGraphView26 setViewerMask 16383
SpatialGraphView26 select
SpatialGraphView26 setPickable 1

set hideNewModules 0


viewer 0 setCameraOrientation 0.579198 0.674142 -0.458326 4.43493
viewer 0 setCameraPosition -329.807 475.806 -384.437
viewer 0 setCameraFocalDistance 703.345
viewer 0 setCameraNearDistance 317.813
viewer 0 setCameraFarDistance 1058.99
viewer 0 setCameraType orthographic
viewer 0 setCameraHeight 1406.69
viewer 0 setAutoRedraw 1
viewer 0 redraw

