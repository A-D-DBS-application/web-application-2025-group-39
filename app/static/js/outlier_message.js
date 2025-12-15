// static/js/outlier_message.js

/**
 * Functie om de outlier-waarschuwing te verwijderen.
 * Gebruikt nu de browser confirm() en verstuurt direct de POST request.
 * @param {string} outlierId - De unieke ID van de outlier.
 */
function confirmAndDismissWarning(outlierId) {
    // Gebruik de standaard browser confirm box
    if (confirm('Are you sure you want to remove this warning?')) {
        
        // 1. Verberg de popover (indien zichtbaar)
        const container = document.getElementById(outlierId + "-container");
        if (container) {
            const triggerEl = container.querySelector('.outlier-trigger');
            // Probeer de Popover te vinden en te verbergen
            const instance = triggerEl ? bootstrap.Popover.getInstance(triggerEl) : null;
            if (instance) instance.hide();
        }

        // 2. Voer de POST request uit
        fetch(`/outliers/${encodeURIComponent(outlierId)}/dismiss`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Herlaad de pagina na succesvolle database-update
                window.location.reload(); 
            } else {
                alert('Could not remove the warning. Please try again.');
            }
        })
        .catch(err => {
            console.error('Failed to dismiss warning:', err);
            alert('An unexpected error occurred.');
        });
    }
}


/**
 * Initialiseert alle Popovers.
 */
document.addEventListener('DOMContentLoaded', () => {
  
  // Hulpfunctie om de Popover te controleren/sluiten
  const hideIfOutside = (popoverInstance, triggerEl) => {
      setTimeout(() => {
        const triggerHovered = triggerEl.matches(':hover');
        // Controleer of de popover instantie en het DOM element bestaan voordat u verder gaat
        const popoverEl = popoverInstance.tip;
        const popoverHovered = popoverEl && popoverEl.matches(':hover');

        if (!triggerHovered && !popoverHovered) {
          popoverInstance.hide();
        }
      }, 100); 
    };

  // 1. INITIALISEER ALLE POPOVERS
  document.querySelectorAll('.outlier-trigger').forEach(triggerEl => {
    const contentId = triggerEl.dataset.bsContentId;
    const contentEl = document.getElementById(contentId);
    if (!contentEl) return;

    // Zorg ervoor dat de Popover niet de trigger 'focus' gebruikt, anders kan deze niet gesloten worden na de click
    const popoverInstance = new bootstrap.Popover(triggerEl, {
      content: contentEl.innerHTML,
      html: true,
      sanitize: false,
      trigger: 'manual', // Alleen handmatig openen/sluiten
      container: 'body',
      placement: 'right'
    });

    // Hover in logica
    triggerEl.addEventListener('mouseenter', () => {
      const container = triggerEl.closest('.outlier-container');
      // Aangezien de waarschuwing in de database permanent is verwijderd, is deze klasse niet meer relevant.
      // We checken nu alleen of de container bestaat.
      if (container) { 
          popoverInstance.show();
          
          setTimeout(() => {
              const popoverEl = popoverInstance.tip;
              if (popoverEl) {
                  // Koppel de sluitlogica aan de Popover-box en de trigger
                  popoverEl.addEventListener('mouseleave', () => hideIfOutside(popoverInstance, triggerEl));
                  triggerEl.addEventListener('mouseleave', () => hideIfOutside(popoverInstance, triggerEl));
                  
                  // Voeg een click handler toe aan de knop in de popover om de popover te sluiten
                  const button = popoverEl.querySelector('.btn-danger-custom');
                  if (button) {
                     button.addEventListener('click', () => popoverInstance.hide());
                  }
              }
          }, 50);
      }
    });

    // Zorg ervoor dat de popover sluit als de muis beweegt
    triggerEl.addEventListener('mouseleave', () => hideIfOutside(popoverInstance, triggerEl));
  });
});