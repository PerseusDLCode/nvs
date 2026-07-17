# Directory Definitions
RAW_DIR := raw
BIN_DIR := bin
SRC_DIR := src/hypervariorum
OUT_DIR := out

# Default target
.PHONY: all
all: pdm_check

# Run PDM install automatically if the lockfile changes
pdm_check: pdm.lock
	pdm install
	@touch pdm_check

# Rule to automatically create the output directory
$(OUT_DIR):
	mkdir -p $(OUT_DIR)

# Rule to generate annotation document
$(OUT_DIR)/%.annot.xml: $(OUT_DIR)/%.cleaned $(BIN_DIR)/parse_annotations.py $(SRC_DIR)/nvs/parsing.py | $(OUT_DIR)
	pdm run python $(BIN_DIR)/parse_annotations.py < $< > $@

# Clean
$(OUT_DIR)/%.cleaned: $(RAW_DIR)/%.txt $(BIN_DIR)/convert_entities.py $(SRC_DIR)/nvs/entities.py pdm_check | $(OUT_DIR)
	pdm run python $(BIN_DIR)/convert_entities.py < $< > $@


$(OUT_DIR)/%.xml: $(OUT_DIR)/%.a $(BIN_DIR)/convert_entities.py $(SRC_DIR)/nvs/entities.py pdm_check | $(OUT_DIR)
	pdm run python $(BIN_DIR)/convert_entities.py < $< > $@



# Clean up all generated files in out/
.PHONY: clean
clean:
	rm -rf $(OUT_DIR) pdm_check
