#include <iostream>
#include <vector>


std::vector< std::pair<float, float> > resonancesToVeto{
    //mass    width 
    {0.5479  ,0.030}, // eta
    {0.7753  ,0.075}, // rho (770)
    {0.7827  ,0.030}, // omega(783)
    {1.0195  ,0.030}, // phi
    {3.0969  ,0.030}, // J/Psi
    {3.6861  ,0.030}, // Psi(2S)
    {9.4603  ,0.070}, // Y
    {10.0233 ,0.070}, // Y(2S)
    {10.3552 ,0.070}, // Y(3S)
    {91.1976 ,2.495}  // Z
}; //resonancesToVeto

constexpr int SIGMA_TO_EXCLUDE = 2;