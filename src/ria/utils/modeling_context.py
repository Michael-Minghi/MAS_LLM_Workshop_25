from dataclasses import dataclass, field
from enum import Enum
import os

class BuildingType(str, Enum):
    LOW_RISE = "low_rise"
    MID_RISE = 'Mid-rise'
    HIGH_RISE = "high_rise"
    Linear = "linear"

class DesignStrategy(str, Enum):
    VANILLA = "continuity"
    NONVANILLA = 'disruptive'

@dataclass
class ModelingContext:
    image_path: str = None
    output_dir: str = None
    name: str = None
    eval_count: int = 0
    material : str = None
    building_type: BuildingType = None
    #TODO Check to fit option 2
    design_strategy: DesignStrategy = None
    design_driver: dict = None
    material_driver: dict = None
    design_task: dict = None
    render_images: list[str] = None
    gh_pyhon_script: str = None
    evaluation: dict = None
    run_flag: dict = field(default_factory=lambda: {
        'design_driver': True,
        'material_driver': True,
        'design_task': True,
        'design_modeling': True,
        'evaluation': True
    })
    modeling_failed: bool = False

    def compose_name(self):
        if all([self.image_path, self.building_type, self.design_strategy]):
            image_id = os.path.basename(self.image_path).split('_')[0]
            strategy_id = list(DesignStrategy).index(self.design_strategy)
            type_id = list(BuildingType).index(self.building_type)
            eval_id = str(self.eval_count).zfill(2)
            self.name = f"{image_id}_S{strategy_id}_T{type_id}_E{eval_id}"
        else:
            raise ValueError("image_path, building_type, and design_strategy must be set to compose the name.")
    
    def check_run_flags(self, target: str):
        flag_map = ['design_driver', 'material_driver', 'design_task', 'design_modeling', 'evaluation']
        index = flag_map.index(target)
        for i, key in enumerate(flag_map):
            if i < index:
                self.run_flag[key] = False
            else:
                self.run_flag[key] = True