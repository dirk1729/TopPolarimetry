#ifndef MCVal_MCValAlg_H
#define MCVal_MCValAlg_H

#include <AnaAlgorithm/AnaAlgorithm.h>
#include <AnaAlgorithm/Global.h>

#include <xAODTruth/TruthParticleContainer.h>
#include <xAODMissingET/MissingETContainer.h>
#include <TH1.h>
#include <TH2.h>
#include <TTree.h>
#include <TLorentzVector.h>
#include <AsgMessaging/MessageCheck.h>
#include <Math/Vector4D.h>
#include <TLorentzVector.h>
#include <AsgMessaging/MessageCheck.h>
#include <xAODEventInfo/EventInfo.h>
#include <xAODTruth/TruthEventContainer.h>
#include <xAODEventInfo/EventInfo.h>
#include <xAODTruth/TruthEventContainer.h>
#include <xAODJet/JetContainer.h>
#include "MCVal/TruthUtils.h"

// namespace MCVal
// {

class MCValAlg : public EL::AnaAlgorithm
{
public:
  // this is a standard algorithm constructor
  MCValAlg (const std::string& name, ISvcLocator* pSvcLocator);

  ~MCValAlg () override;

  // these are the functions inherited from Algorithm
  virtual StatusCode initialize () override;
  virtual StatusCode execute () override;
  virtual StatusCode finalize () override;

private:

  // Event properties to save
  unsigned int m_runNumber = 0; ///< Run number
  unsigned long long m_eventNumber = 0; ///< Event number

  std::vector<float>* m_t_pt;
  std::vector<float>* m_t_eta;
  std::vector<float>* m_t_phi;
  std::vector<float>* m_t_e;
  std::vector<float>* m_t_m;
  std::vector<int>*   m_t_pid;
  std::vector<int>*   m_t_parent_pid;

  std::vector<float>* m_W_pt;
  std::vector<float>* m_W_eta;
  std::vector<float>* m_W_phi;
  std::vector<float>* m_W_e;
  std::vector<int>* m_W_pid;

  std::vector<float>* m_W_l_pt;
  std::vector<float>* m_W_l_eta;
  std::vector<float>* m_W_l_phi;
  std::vector<float>* m_W_l_e;
  std::vector<int>*   m_W_l_pid;

  std::vector<float>* m_W_n_pt;
  std::vector<float>* m_W_n_eta;
  std::vector<float>* m_W_n_phi;
  std::vector<float>* m_W_n_e;
  std::vector<int>*   m_W_n_pid;

  std::vector<float>* m_b_pt;
  std::vector<float>* m_b_eta;
  std::vector<float>* m_b_phi;
  std::vector<float>* m_b_e;
  std::vector<int>*   m_b_pid;

  std::vector<float>* m_lrjet_pt;
  std::vector<float>* m_costheta;
};

// } // namespace MCVal

#endif
