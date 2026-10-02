#include <MCVal/MCValAlg.h>
// namespace MCVal
// {

MCValAlg :: MCValAlg (const std::string& name,
                     ISvcLocator *pSvcLocator)
  : EL::AnaAlgorithm (name, pSvcLocator)
{
}

StatusCode MCValAlg :: initialize ()
{
  ANA_CHECK(book(TTree("analysis","analysis")));
  TTree* t = tree("analysis");

  t->Branch("RunNumber",&m_runNumber);
  t->Branch("EventNumber",&m_eventNumber);
  // Initialize vectors 
  m_t_pt = new std::vector<float>();
  m_t_eta = new std::vector<float>();
  m_t_phi = new std::vector<float>();
  m_t_e = new std::vector<float>();
  m_t_m = new std::vector<float>();
  m_t_pid = new std::vector<int>();
  m_t_parent_pid = new std::vector<int>();

  m_W_pt     = new std::vector<float>();
  m_W_eta    = new std::vector<float>();
  m_W_phi    = new std::vector<float>();
  m_W_e      = new std::vector<float>();
  m_W_pid    = new std::vector<int>();

  m_W_l_pt  = new std::vector<float>();
  m_W_l_eta = new std::vector<float>();
  m_W_l_phi = new std::vector<float>();
  m_W_l_e   = new std::vector<float>();
  m_W_l_pid = new std::vector<int>();

  m_W_n_pt  = new std::vector<float>();
  m_W_n_eta = new std::vector<float>();
  m_W_n_phi = new std::vector<float>();
  m_W_n_e   = new std::vector<float>();
  m_W_n_pid = new std::vector<int>();

  m_b_pt  = new std::vector<float>();
  m_b_eta = new std::vector<float>();
  m_b_phi = new std::vector<float>();
  m_b_e   = new std::vector<float>();

  m_costheta = new std::vector<float>();

  t->Branch("t_pt",  &m_t_pt);
  t->Branch("t_eta", &m_t_eta);
  t->Branch("t_phi", &m_t_phi);
  t->Branch("t_e",   &m_t_e);
  t->Branch("t_m", &m_t_m);
  t->Branch("t_pid", &m_t_pid);
  t->Branch("t_parent_pid", &m_t_parent_pid);

  t->Branch("W_pt",  &m_W_pt);
  t->Branch("W_eta", &m_W_eta);
  t->Branch("W_phi", &m_W_phi);
  t->Branch("W_e",   &m_W_e);
  t->Branch("W_pid", &m_W_pid);

  t->Branch("W_l_pt",  &m_W_l_pt);
  t->Branch("W_l_eta", &m_W_l_eta);
  t->Branch("W_l_phi", &m_W_l_phi);
  t->Branch("W_l_e",   &m_W_l_e);
  t->Branch("W_l_pid", &m_W_l_pid);

  t->Branch("W_n_pt",  &m_W_n_pt);
  t->Branch("W_n_eta", &m_W_n_eta);
  t->Branch("W_n_phi", &m_W_n_phi);
  t->Branch("W_n_e",   &m_W_n_e);
  t->Branch("W_n_pid", &m_W_n_pid);

  t->Branch("b_pt",&m_b_pt);
  t->Branch("b_eta",&m_b_eta);
  t->Branch("b_phi",&m_b_phi);
  t->Branch("b_e",&m_b_e);

  // m_lrjet_pt = new std::vector<float>();
  // t->Branch("lrjet_pt", &m_lrjet_pt);

  t->Branch("costheta", &m_costheta);

  // ANA_CHECK( book( TH1F("h_N_q","h_N_q",50,0,600) ) );
  ANA_CHECK( book( TH1F("h_top_pt","top_pt",50,0,1000) ) );
  ANA_CHECK( book( TH1F("h_top_eta","top_eta",50,-4.0,4.0) ) );
  ANA_CHECK( book( TH1F("h_top_phi","top_phi",50,-3.2,3.2) ) );

  ANA_CHECK( book( TH1F("h_W_pt","W_pt",50,0,1000) ) );
  ANA_CHECK( book( TH1F("h_W_eta","W_eta",50,-4.0,4.0) ) );
  ANA_CHECK( book( TH1F("h_W_phi","W_phi",50,-3.2,3.2) ) );

  ANA_CHECK( book( TH1F("h_W_child_pt","W_child_pt",50,0,1000) ) );
  ANA_CHECK( book( TH1F("h_W_child_eta","W_child_eta",50,-4.0,4.0) ) );
  ANA_CHECK( book( TH1F("h_W_child_phi","W_child_phi",50,-3.2,3.2) ) );
  ANA_CHECK( book( TH1F("h_W_child_pdgID", "W_child_pdgID", 50, -20, 20)));

  ANA_CHECK( book( TH1F("h_bottom_pt","bottom_pt",50,0,1000) ) );
  ANA_CHECK( book( TH1F("h_bottom_eta","bottom_eta",50,-4.0,4.0) ) );
  ANA_CHECK( book( TH1F("h_bottom_phi","bottom_phi",50,-3.2,3.2) ) );

  ANA_CHECK( book( TH1F("h_cos_theta", "cos_theta", 35, -1, 1)));



  return StatusCode::SUCCESS;
}

StatusCode MCValAlg :: execute ()
{
  setFilterPassed(false);

  const xAOD::EventInfo* ei=nullptr;
  ANA_CHECK(evtStore()->retrieve(ei,"EventInfo"));
  // const xAOD::JetContainer* jets = nullptr;
  // ANA_CHECK(evtStore()->retrieve(jets, "AntiKt10TruthTrimmedPtFrac5SmallR20Jets"));

  m_runNumber   = ei->runNumber();
  m_eventNumber= ei->eventNumber();

  const xAOD::TruthParticleContainer* truth=nullptr;
  ANA_CHECK(evtStore()->retrieve(truth,"TruthParticles"));

  // ======================================================
  // Loop over ALL tops
  // ======================================================

  TLorentzVector vbm;
  TLorentzVector vbp;
  TLorentzVector vWm;
  TLorentzVector vWp;

  for (const xAOD::TruthParticle* top : *truth) {

    if(abs(top->pdgId())!=6) continue;
    if(!top->hasDecayVtx()) continue;

    const xAOD::TruthVertex* vertex = top->production_vertex();
    if (vertex==0) continue;

    int nin = vertex->nIncomingParticles();
    if (nin==0) continue;

    const xAOD::TruthParticle* parent = vertex->incomingParticle(0);
    if (parent==0) continue;

    hist("h_top_pt")->Fill(top->pt()/Truth::GeV);
    hist("h_top_eta")->Fill(top->eta());
    hist("h_top_phi")->Fill(top->phi());

    m_t_pt->push_back(top->pt());
    m_t_eta->push_back(top->eta());
    m_t_phi->push_back(top->phi());
    m_t_e->push_back(top->e());
    m_t_m->push_back(top->m());
    m_t_pid->push_back(top->pdgId());
    m_t_parent_pid->push_back(parent->pdgId());



    // bool isT  = top->pdgId()==6;
    // bool isTbar = top->pdgId()==-6;

    const xAOD::TruthVertex* tvtx = top->decayVtx();

    for (size_t i=0; i<tvtx->nOutgoingParticles(); ++i) {
      const xAOD::TruthParticle* child = tvtx->outgoingParticle(i);
      if(!child) continue;


      if (child->pdgId()==5) {
        vbp.SetPtEtaPhiE(child->pt(), child->eta(), child->phi(), child->e());
      } else if (child->pdgId()==-5) {
        vbm.SetPtEtaPhiE(child->pt(), child->eta(), child->phi(), child->e());
      }

      if(abs(child->pdgId())==5) { 
        hist("h_bottom_pt")->Fill(child->pt()/Truth::GeV);
        hist("h_bottom_eta")->Fill(child->eta());
        hist("h_bottom_phi")->Fill(child->phi());
        m_b_pt ->push_back(child->pt());
        m_b_eta->push_back(child->eta());
        m_b_phi->push_back(child->phi());
        m_b_e  ->push_back(child->e());
      }

      // =========================
      // W from top
      // =========================
      if (abs(child->pdgId())!=24) continue;
      if (!child->hasDecayVtx()) continue;


      if (child->pdgId()==24) {
        vWp.SetPtEtaPhiE(child->pt(), child->eta(), child->phi(), child->e());
      } else {
        vWm.SetPtEtaPhiE(child->pt(), child->eta(), child->phi(), child->e());
      }
      hist("h_W_pt")->Fill(child->pt()/Truth::GeV);
      hist("h_W_eta")->Fill(child->eta());
      hist("h_W_phi")->Fill(child->phi());
      m_W_pt ->push_back(child->pt());
      m_W_eta->push_back(child->eta());
      m_W_phi->push_back(child->phi());
      m_W_e  ->push_back(child->e());
      m_W_pid->push_back(child->pdgId());

      const xAOD::TruthVertex* Wvtx = child->decayVtx();

      for (size_t j=0; j<Wvtx->nOutgoingParticles(); ++j) {

        const xAOD::TruthParticle* Wchild = Wvtx->outgoingParticle(j);
        if (!Wchild) continue;

          hist("h_W_child_pt")->Fill(Wchild->pt()/Truth::GeV);
          hist("h_W_child_eta")->Fill(Wchild->eta());
          hist("h_W_child_phi")->Fill(Wchild->phi());
          hist("h_W_child_pdgID")->Fill(Wchild->pdgId());

        if (Wchild->pdgId()==11 || Wchild->pdgId()==13) {
          m_W_l_pt ->push_back(Wchild->pt());
          m_W_l_eta->push_back(Wchild->eta());
          m_W_l_phi->push_back(Wchild->phi());
          m_W_l_e  ->push_back(Wchild->e());
          m_W_l_pid->push_back(Wchild->pdgId());
        }
        if (Wchild->pdgId()==-12 || Wchild->pdgId()==-14) {
          m_W_n_pt ->push_back(Wchild->pt());
          m_W_n_eta->push_back(Wchild->eta());
          m_W_n_phi->push_back(Wchild->phi());
          m_W_n_e  ->push_back(Wchild->e());
          m_W_n_pid->push_back(Wchild->pdgId());
        }
      }
    }
  }

  // Calculate costheta after all tops have been processed
  TLorentzVector vtp = vWp + vbp;
  TLorentzVector vtm = vWm + vbm;

  TVector3 boost_tt = (vtm + vtp).BoostVector();
  vtp.Boost(-boost_tt);
  vtm.Boost(-boost_tt);
  vbp.Boost(-boost_tt);
  vbm.Boost(-boost_tt);

  // Now boost b-quark to the top+ rest frame and calculate angle
  TVector3 boost_tp = vtp.BoostVector();
  vbp.Boost(-boost_tp);

  // cos(theta*) is the angle between b and top direction
  float costheta = vtp.Vect().Unit().Dot(vbp.Vect().Unit());
  hist("h_cos_theta")->Fill(costheta);
  m_costheta->push_back(costheta);



  tree("analysis")->Fill();
  m_t_pt->clear();
  m_t_eta->clear();
  m_t_phi->clear();
  m_t_e->clear();
  m_t_m->clear();
  m_t_pid->clear();
  m_t_parent_pid->clear();

  m_W_pt->clear();
  m_W_eta->clear();
  m_W_phi->clear();
  m_W_e->clear();
  m_W_pid->clear();

  m_W_l_pt->clear();
  m_W_l_eta->clear();
  m_W_l_phi->clear();
  m_W_l_e->clear();
  m_W_l_pid->clear();

  m_W_n_pt->clear();
  m_W_n_eta->clear();
  m_W_n_phi->clear();
  m_W_n_e->clear();
  m_W_n_pid->clear();

  m_b_pt->clear();
  m_b_eta->clear();
  m_b_phi->clear();
  m_b_e->clear();

  // m_lrjet_pt->clear();
  m_costheta->clear();

  setFilterPassed(true);
  return StatusCode::SUCCESS;
}

StatusCode MCValAlg :: finalize ()
{
  return StatusCode::SUCCESS;
}

MCValAlg :: ~MCValAlg ()
{
  delete m_t_pt;
  delete m_t_eta;
  delete m_t_phi;
  delete m_t_e;
  delete m_t_m;
  delete m_t_pid;
  delete m_t_parent_pid;

  delete m_W_pt;
  delete m_W_eta;
  delete m_W_phi;
  delete m_W_e;
  delete m_W_pid;

  delete m_W_l_pt;
  delete m_W_l_eta;
  delete m_W_l_phi;
  delete m_W_l_e;
  delete m_W_l_pid;

  delete m_W_n_pt;
  delete m_W_n_eta;
  delete m_W_n_phi;
  delete m_W_n_e;
  delete m_W_n_pid;

  delete m_b_pt;
  delete m_b_eta;
  delete m_b_phi;
  delete m_b_e;

  // delete m_lrjet_pt;
  delete m_costheta;
}

// } // namespace MCVal
