// static/js/outlier_message.js

/**
 * Functie om de outlier-waarschuwing te verwijderen.
 * @param {string} outlierId - De unieke ID van de outlier.
 * @param {HTMLElement} removeButton - De 'Remove' knop die geklikt is.
 */
function removeOutlierWarning(outlierId, btn) {
  // Zoek de container die het icoon en de popover bevat
  const container = document.getElementById(outlierId + "-container");
  if (container) {
    container.remove(); // haalt het hele icoon + popover weg
  }

  // Verberg de Popover direct
  const triggerEl = container.querySelector('.outlier-trigger');
  const instance = triggerEl ? bootstrap.Popover.getInstance(triggerEl) : null;
  if (instance) instance.hide();

  // Open modal en sla het ID op in dataset
  const modalEl = document.getElementById('removeConfirmModal');
  const modal = new bootstrap.Modal(modalEl);
  modalEl.dataset.outlierId = outlierId;
  modal.show();
}

/**
 * Controleert bij het laden van de pagina of er verborgen outliers zijn 
 * en initialiseert alle Popovers + modal logica.
 */
document.addEventListener('DOMContentLoaded', () => {
  
  // NIEUW: Hulpfunctie om de Popover te controleren/sluiten
  const hideIfOutside = (popoverInstance, triggerEl) => {
      setTimeout(() => {
        const triggerHovered = triggerEl.matches(':hover');
        const popoverEl = popoverInstance.tip;
        const popoverHovered = popoverEl && popoverEl.matches(':hover');

        if (!triggerHovered && !popoverHovered) {
          popoverInstance.hide();
        }
      }, 100); // Korte vertraging (100ms)
    };

  // 1. INITIALISEER ALLE POPOVERS (met de nieuwe, snellere mouseleave logica)
  document.querySelectorAll('.outlier-trigger').forEach(triggerEl => {
    const contentId = triggerEl.dataset.bsContentId;
    const contentEl = document.getElementById(contentId);
    if (!contentEl) return;

    const popoverInstance = new bootstrap.Popover(triggerEl, {
      content: contentEl.innerHTML,
      html: true,
      sanitize: false,
      trigger: 'manual',
      container: 'body',
      placement: 'right'
    });

    // Hover in
    triggerEl.addEventListener('mouseenter', () => {
      const container = triggerEl.closest('.outlier-container');
      if (container && !container.classList.contains('is-hidden')) {
          popoverInstance.show();
          
          setTimeout(() => {
              const popoverEl = popoverInstance.tip;
              if (popoverEl) {
                  // Koppel de sluitlogica aan de Popover-box en de trigger
                  popoverEl.addEventListener('mouseleave', () => hideIfOutside(popoverInstance, triggerEl));
                  triggerEl.addEventListener('mouseleave', () => hideIfOutside(popoverInstance, triggerEl));
              }
          }, 50);
      }
    });
    // Oorspronkelijke mouseleave-logica is verwijderd en vervangen door de dynamische koppeling
  });

  // 2. Koppel de confirm-knop van de modal
  const confirmBtn = document.getElementById('confirmRemoveBtn');
  confirmBtn.addEventListener('click', () => {
    const modalEl = document.getElementById('removeConfirmModal');
    const outlierId = modalEl.dataset.outlierId;
    if (!outlierId) return;

    const container = document.getElementById(outlierId + '-container');
    
    // Zoek de trigger en de Popover instantie
    const triggerEl = document.querySelector(
      '.outlier-trigger[data-bs-content-id="popover-content-' + outlierId + '"]'
    );
    const instance = triggerEl ? bootstrap.Popover.getInstance(triggerEl) : null;

    // FIX: Popover permanent verwijderen (dispose) en verbergen
    if (instance) {
        instance.hide(); 
        instance.dispose(); // <-- GARANDEERT DAT DE ZWEVENDE POPUP WEG IS
    }

    // De container met het icoon verbergen
    if (container) {
      container.classList.add('is-hidden');
    }
    
    // Bewaar status in Local Storage
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + 21);
    localStorage.setItem(outlierId, JSON.stringify({ hidden: true, expiry: expiryDate.getTime() }));

    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();
  });

  // 3. CONTROLEER LOCAL STORAGE BIJ HET LADEN VAN DE PAGINA
  document.querySelectorAll('.outlier-container').forEach(container => {
    const outlierId = container.dataset.outlierId;
    // NIEUW: Controle op lege ID
    if (!outlierId) return; 
    
    const storedItem = localStorage.getItem(outlierId);
    if (storedItem) {
      try {
        const data = JSON.parse(storedItem);
        const now = Date.now();
        // VOEG DE IS-HIDDEN CLASSE TOE ALS DE STATUS IS OPGESLAGEN EN NOG GELDIG IS
        if (data.hidden && data.expiry > now) {
          container.classList.add('is-hidden');
        } else if (data.expiry <= now) {
          localStorage.removeItem(outlierId);
        }
      } catch (e) {
        console.error("Fout bij parsen van Local Storage data:", e);
        localStorage.removeItem(outlierId);
      }
    }
  });
});