"""
Kiko 反射单元建模固定配置
Background、Boundaries、zmax 计算
"""

# 光速 mm/s，用于计算半波长
C_MM_PER_S = 299792458000.0


def zmax_from_freq_ghz(freq_ghz: float) -> float:
    """中心频率的 1/2 波长 (mm)。zmax = λ/2 = c/(2*f)"""
    if freq_ghz <= 0:
        return 61.22  # 默认 2.45 GHz 对应值
    return C_MM_PER_S / (2.0 * freq_ghz * 1e9)


def background_vba(zmax_mm: float) -> str:
    """Kiko 固定 Background VBA。zmax 已通过 StoreDoubleParameter 设置。"""
    return '''Sub Main
With Background
    .ResetBackground
    .XminSpace "0.0"
    .XmaxSpace "0.0"
    .YminSpace "0.0"
    .YmaxSpace "0.0"
    .ZminSpace "0.0"
    .ZmaxSpace "zmax"
    .ApplyInAllDirections "False"
End With

With Material
    .Reset
    .Rho "0"
    .ThermalType "Normal"
    .ThermalConductivity "0"
    .SpecificHeat "0", "J/K/kg"
    .DynamicViscosity "0"
    .UseEmissivity "True"
    .Emissivity "0"
    .MetabolicRate "0.0"
    .VoxelConvection "0.0"
    .BloodFlow "0"
    .Absorptance "0"
    .MechanicsType "Unused"
    .IntrinsicCarrierDensity "0"
    .FrqType "all"
    .Type "Normal"
    .MaterialUnit "Frequency", "Hz"
    .MaterialUnit "Geometry", "m"
    .MaterialUnit "Time", "s"
    .MaterialUnit "Temperature", "K"
    .Epsilon "1.0"
    .Mu "1.0"
    .Sigma "0"
    .TanD "0.0"
    .TanDFreq "0.0"
    .TanDGiven "False"
    .TanDModel "ConstSigma"
    .SetConstTanDStrategyEps "AutomaticOrder"
    .ConstTanDModelOrderEps "3"
    .DjordjevicSarkarUpperFreqEps "0"
    .SetElParametricConductivity "False"
    .ReferenceCoordSystem "Global"
    .CoordSystemType "Cartesian"
    .SigmaM "0"
    .TanDM "0.0"
    .TanDMFreq "0.0"
    .TanDMGiven "False"
    .TanDMModel "ConstSigma"
    .SetConstTanDStrategyMu "AutomaticOrder"
    .ConstTanDModelOrderMu "3"
    .DjordjevicSarkarUpperFreqMu "0"
    .SetMagParametricConductivity "False"
    .DispModelEps "None"
    .DispModelMu "None"
    .DispersiveFittingSchemeEps "Nth Order"
    .MaximalOrderNthModelFitEps "10"
    .ErrorLimitNthModelFitEps "0.1"
    .UseOnlyDataInSimFreqRangeNthModelEps "False"
    .DispersiveFittingSchemeMu "Nth Order"
    .MaximalOrderNthModelFitMu "10"
    .ErrorLimitNthModelFitMu "0.1"
    .UseOnlyDataInSimFreqRangeNthModelMu "False"
    .UseGeneralDispersionEps "False"
    .UseGeneralDispersionMu "False"
    .NLAnisotropy "False"
    .NLAStackingFactor "1"
    .NLADirectionX "1"
    .NLADirectionY "0"
    .NLADirectionZ "0"
    .Colour "0.6", "0.6", "0.6"
    .Wireframe "False"
    .Reflection "False"
    .Allowoutline "True"
    .Transparentoutline "False"
    .Transparency "0"
    .ChangeBackgroundMaterial
End With
End Sub'''


def boundaries_vba() -> str:
    """Kiko 固定 Boundaries：FloquetPort，x/y unit cell，z open。"""
    return '''Sub Main
With FloquetPort
    .Reset
    .SetDialogTheta "0"
    .SetDialogPhi "0"
    .SetPolarizationIndependentOfScanAnglePhi "0.0", "False"
    .SetSortCode "+beta/pw"
    .SetCustomizedListFlag "False"
    .Port "Zmin"
    .SetNumberOfModesConsidered "2"
    .SetDistanceToReferencePlane "-zmax"
    .SetUseCircularPolarization "False"
    .Port "Zmax"
    .SetNumberOfModesConsidered "2"
    .SetDistanceToReferencePlane "-zmax"
    .SetUseCircularPolarization "False"
End With
End Sub'''


def unit_cell_boundaries_vba() -> str:
    """x、y 边界为 unit cell，z 为 expanded open（add space）。"""
    return '''Sub Main
With Boundary
    .Xmin "unit cell"
    .Xmax "unit cell"
    .Ymin "unit cell"
    .Ymax "unit cell"
    .Zmin "expanded open"
    .Zmax "expanded open"
End With
End Sub'''
