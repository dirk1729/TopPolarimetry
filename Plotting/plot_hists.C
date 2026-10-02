#include <TFile.h>
#include <TKey.h>
#include <TH1.h>
#include <TCanvas.h>
#include <TSystem.h>

#include "atlasrootstyle/AtlasStyle.C"
#include "atlasrootstyle/AtlasLabels.C"
#include "atlasrootstyle/AtlasUtils.C"

void plot_hists(const char* filename="input.root", const char* output_folder="output") {

  SetAtlasStyle();

  TFile *f = TFile::Open(filename);
  if (!f || f->IsZombie()) {
    printf("Could not open file\n");
    return;
  }

  TString outDir = output_folder;
  if (!outDir.EndsWith("/")) {
    outDir += "/";
  }
  gSystem->mkdir(outDir, true);

  TCanvas c("c","c",800,600);

  TIter next(f->GetListOfKeys());
  TKey *key;

  while ((key = (TKey*)next())) {

    TObject *obj = key->ReadObj();
    if (!obj->InheritsFrom("TH1")) continue;

    TH1 *h = (TH1*)obj;

    c.Clear();

    // ---- Axis titles & plot title ----
    h->SetTitle(h->GetTitle());  // histogram title
    h->GetXaxis()->SetTitle(h->GetXaxis()->GetTitle());
    h->GetYaxis()->SetTitle(h->GetYaxis()->GetTitle());

    // Styling
    h->SetLineWidth(2);
    h->GetXaxis()->SetTitleOffset(1.2);
    h->GetYaxis()->SetTitleOffset(1.4);

    h->Draw("hist");

    // ATLAS label
    ATLASLabel(0.20, 0.85, "Internal");

    TString name = h->GetName();
    c.SaveAs(outDir + name + ".pdf");
  }

  f->Close();
}
